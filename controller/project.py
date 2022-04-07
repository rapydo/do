"""
Utilities to handle projects' structure
"""
import os
import re
from pathlib import Path
from typing import List, Optional

from controller import (
    BACKUP_DIR,
    DATA_DIR,
    LOGS_FOLDER,
    PROJECT_DIR,
    SUBMODULES_DIR,
    log,
    print_and_exit,
)
from controller.utilities import git

NO_AUTHENTICATION = "NO_AUTHENTICATION"
NO_FRONTEND = "nofrontend"
ANGULAR = "angular"
GITKEEP = ".gitkeep"


class Project:
    def __init__(self) -> None:
        self.expected_main_folders: List[Path] = [PROJECT_DIR, DATA_DIR, SUBMODULES_DIR]
        # Will be verifed by check and added by create
        self.expected_folders: List[Path] = []
        self.expected_files: List[Path] = []
        # Copied as they are, no templating (used for binary files, like images)
        self.raw_files: List[Path] = []
        # Intended to be immutable, check will raise warning when differs
        self.fixed_files: List[Path] = []
        # Not verified, added by create if --add-optionals
        self.optionals_folders: List[Path] = []
        self.optionals_files: List[Path] = []
        # Created in data if missing
        self.data_folders: List[Path] = []
        self.data_files: List[Path] = []
        # check will raise an error if these files will be found
        self.obsolete_files: List[Path] = []
        self.suggested_gitkeep: List[Path] = []

    def p_path(self, *args: str) -> Path:
        return PROJECT_DIR.joinpath(self.project, *args)

    def load_project_scaffold(
        self, project: str, auth: Optional[str], services: Optional[List[str]] = None
    ) -> bool:

        if services is None:
            services = []

        self.project = project
        self.expected_folders.extend(self.expected_main_folders)
        self.expected_folders.append(self.p_path("confs"))
        self.expected_folders.append(self.p_path("builds"))
        self.expected_folders.append(self.p_path("backend"))
        self.expected_folders.append(self.p_path("backend", "endpoints"))
        self.expected_folders.append(self.p_path("backend", "models"))
        self.expected_folders.append(self.p_path("backend", "models", "emails"))
        self.expected_folders.append(self.p_path("backend", "tasks"))
        self.expected_folders.append(self.p_path("backend", "tests"))
        self.expected_folders.append(self.p_path("backend", "cron"))

        self.suggested_gitkeep.append(SUBMODULES_DIR.joinpath(GITKEEP))
        self.suggested_gitkeep.append(DATA_DIR.joinpath(GITKEEP))
        self.suggested_gitkeep.append(LOGS_FOLDER.joinpath(GITKEEP))
        self.suggested_gitkeep.append(BACKUP_DIR.joinpath(GITKEEP))
        self.suggested_gitkeep.append(self.p_path("backend", "cron", GITKEEP))
        self.suggested_gitkeep.append(self.p_path("builds", GITKEEP))
        self.suggested_gitkeep.append(self.p_path("backend", "endpoints", GITKEEP))
        self.suggested_gitkeep.append(self.p_path("backend", "tasks", GITKEEP))
        self.suggested_gitkeep.append(self.p_path("backend", "tests", GITKEEP))
        self.suggested_gitkeep.append(
            self.p_path("backend", "models", "emails", GITKEEP)
        )

        self.expected_files.append(self.p_path("project_configuration.yaml"))
        self.expected_files.append(self.p_path("confs", "commons.yml"))
        self.expected_files.append(self.p_path("confs", "development.yml"))
        self.expected_files.append(self.p_path("confs", "production.yml"))
        # Need to ensure mypy to correctly extract typing from the project module
        self.expected_files.append(self.p_path("backend", "__init__.py"))
        self.expected_files.append(self.p_path("backend", "initialization.py"))
        self.expected_files.append(self.p_path("backend", "customization.py"))
        self.expected_files.append(self.p_path("backend", "endpoints", "__init__.py"))
        self.expected_files.append(self.p_path("backend", "models", "__init__.py"))
        self.expected_files.append(self.p_path("backend", "tasks", "__init__.py"))
        self.expected_files.append(self.p_path("backend", "tests", "__init__.py"))
        self.expected_files.append(Path(".gitignore"))
        self.expected_files.append(Path(".gitattributes"))
        self.expected_files.append(Path("pyproject.toml"))
        self.expected_files.append(Path(".flake8"))
        self.expected_files.append(Path(".prettierignore"))

        self.fixed_files.append(Path(".gitattributes"))
        self.fixed_files.append(Path("pyproject.toml"))

        if auth or services:

            models = self.p_path("backend", "models")
            if auth == "sqlalchemy" or "postgres" in services or "mysql" in services:
                self.expected_files.append(models.joinpath("sqlalchemy.py"))
            if auth == "neo4j" or "neo4j" in services:
                self.expected_files.append(models.joinpath("neo4j.py"))

        self.optionals_folders.append(self.p_path("backend", "models", "emails"))
        self.optionals_files.append(
            self.p_path("backend", "models", "emails", "activate_account.html")
        )
        self.optionals_files.append(
            self.p_path("backend", "models", "emails", "new_credentials.html")
        )
        self.optionals_files.append(
            self.p_path("backend", "models", "emails", "reset_password.html")
        )
        self.optionals_files.append(
            self.p_path("backend", "models", "emails", "update_credentials.html")
        )
        self.optionals_files.append(Path("codecov.yml"))

        self.data_folders.extend(
            [
                LOGS_FOLDER,
                BACKUP_DIR,
                DATA_DIR.joinpath("uploads"),
            ]
        )

        # Removed since 0.7.1
        self.obsolete_files.append(self.p_path("confs", "debug.yml"))
        # Removed since 0.7.4
        self.obsolete_files.append(SUBMODULES_DIR.joinpath("rapydo-confs"))
        # Removed since 0.7.5
        self.obsolete_files.append(SUBMODULES_DIR.joinpath("frontend"))
        # Removed since 0.7.6
        self.obsolete_files.append(self.p_path("backend", "apis"))
        # Removed since 0.8
        self.obsolete_files.append(self.p_path("backend", "models", "swagger.yaml"))
        self.obsolete_files.append(self.p_path("backend", "endpoints", "profile.py"))
        # Removed since 0.9
        self.obsolete_files.append(self.p_path("backend", "initialization"))
        self.obsolete_files.append(self.p_path("frontend", "assets", "favicon.ico"))
        # Removed since 1.2
        self.obsolete_files.append(Path(".pre-commit-config.yaml"))
        # Removed since 2.3
        self.obsolete_files.append(Path(".isort.cfg"))
        return True

    def load_frontend_scaffold(self, frontend: Optional[str]) -> bool:
        self.frontend = frontend

        if self.frontend is None or self.frontend == NO_FRONTEND:
            log.debug("No frontend framework enabled")
            return False

        self.expected_folders.append(self.p_path("frontend"))

        if self.frontend == ANGULAR:
            self.expected_folders.extend(
                [
                    self.p_path("frontend", "app"),
                    self.p_path("frontend", "styles"),
                    self.p_path("frontend", "integration"),
                    self.p_path("frontend", "assets"),
                    self.p_path("frontend", "assets", "favicon"),
                ]
            )

            self.suggested_gitkeep.append(
                DATA_DIR.joinpath(self.project, "frontend", GITKEEP)
            )

            self.suggested_gitkeep.append(
                self.p_path("frontend", "integration", GITKEEP)
            )

            self.expected_files.extend(
                [
                    self.p_path("frontend", "package.json"),
                    self.p_path("frontend", "styles", "style.scss"),
                    self.p_path("frontend", "styles", "variables.scss"),
                    self.p_path("frontend", "app", "customization.ts"),
                    self.p_path("frontend", "app", "custom.module.ts"),
                    self.p_path("frontend", "app", "custom.navbar.ts"),
                    self.p_path("frontend", "app", "custom.footer.ts"),
                    self.p_path("frontend", "app", "custom.profile.ts"),
                    self.p_path("frontend", "app", "custom.navbar.links.html"),
                    self.p_path("frontend", "app", "custom.navbar.brand.html"),
                    self.p_path("frontend", "app", "custom.footer.html"),
                    self.p_path("frontend", "app", "custom.profile.html"),
                    self.p_path("frontend", "app", "types.ts"),
                ]
            )
            self.raw_files.extend(
                [
                    # Generated with https://realfavicongenerator.net
                    self.p_path(
                        "frontend", "assets", "favicon", "android-chrome-192x192.png"
                    ),
                    self.p_path("frontend", "assets", "favicon", "browserconfig.xml"),
                    self.p_path("frontend", "assets", "favicon", "favicon-32x32.png"),
                    self.p_path("frontend", "assets", "favicon", "mstile-150x150.png"),
                    self.p_path(
                        "frontend", "assets", "favicon", "safari-pinned-tab.svg"
                    ),
                    self.p_path(
                        "frontend", "assets", "favicon", "apple-touch-icon.png"
                    ),
                    self.p_path("frontend", "assets", "favicon", "favicon-16x16.png"),
                    self.p_path("frontend", "assets", "favicon", "favicon.ico"),
                    self.p_path("frontend", "assets", "favicon", "site.webmanifest"),
                ]
            )

            frontend_data_dir = DATA_DIR.joinpath(self.project, "frontend")
            self.data_folders.extend(
                [
                    frontend_data_dir,
                    frontend_data_dir.joinpath("app"),
                    frontend_data_dir.joinpath("node_modules"),
                    DATA_DIR.joinpath(self.project, "karma"),
                    DATA_DIR.joinpath(self.project, "cypress"),
                ]
            )

            self.data_files.extend(
                [
                    frontend_data_dir.joinpath("angular.json"),
                    frontend_data_dir.joinpath("karma.conf.js"),
                    frontend_data_dir.joinpath("package.json"),
                    frontend_data_dir.joinpath("polyfills.ts"),
                    frontend_data_dir.joinpath("tsconfig.json"),
                    frontend_data_dir.joinpath("tsconfig.app.json"),
                    frontend_data_dir.joinpath("tsconfig.spec.json"),
                    frontend_data_dir.joinpath("tsconfig.server.json"),
                    frontend_data_dir.joinpath("cypress.json"),
                ]
            )

            self.obsolete_files.extend(
                [
                    self.p_path("frontend", "app", "app.routes.ts"),
                    self.p_path("frontend", "app", "app.declarations.ts"),
                    self.p_path("frontend", "app", "app.providers.ts"),
                    self.p_path("frontend", "app", "app.imports.ts"),
                    self.p_path("frontend", "app", "app.custom.navbar.ts"),
                    self.p_path("frontend", "app", "app.custom.navbar.html"),
                    self.p_path("frontend", "app", "app.entryComponents.ts"),
                    self.p_path("frontend", "app", "app.home.ts"),
                    self.p_path("frontend", "app", "app.home.html"),
                    self.p_path("frontend", "app", "custom.declarations.ts"),
                    self.p_path("frontend", "app", "custom.routes.ts"),
                    self.p_path("frontend", "app", "custom.project.options.ts"),
                    # Removed since 1.0
                    frontend_data_dir.joinpath("browserslist"),
                    # Removed since 1.2 (replaced with scss in styles)
                    self.p_path("frontend", "css"),
                ]
            )

        return True

    @staticmethod
    def get_project(project: Optional[str], ignore_multiples: bool = False) -> str:

        projects = os.listdir(PROJECT_DIR)

        if project is None:

            if len(projects) == 0:
                print_and_exit("No project found (is {} folder empty?)", PROJECT_DIR)

            if len(projects) > 1:

                # It is used by the preliminary get used to load the commands
                # In case of multiple projects without a proper definition in
                # projectrc, the custom commands will not be loaded
                if ignore_multiples:
                    return ""

                print_and_exit(
                    "Multiple projects found, "
                    "please use --project to specify one of the following: {}",
                    ", ".join(projects),
                )

            project = projects.pop()

        elif project not in projects:
            print_and_exit(
                "Wrong project {}\nSelect one of the following: {}\n",
                project,
                ", ".join(projects),
            )

        # In case of errors this function will exit
        Project.check_invalid_characters(project)

        if project in Project.reserved_project_names:
            print_and_exit(
                "You selected a reserved name, invalid project name: {}", project
            )

        return project

    @staticmethod
    def check_invalid_characters(project: str) -> None:
        if len(project) <= 1:
            print_and_exit("Wrong project name, expected at least two characters")

        if not re.match("^[a-z][a-z0-9]+$", project):

            # First character is expected to be a-z
            tmp_str = re.sub("[a-z]", "", project[0])
            # Other characters are expected to be a-z 0-9
            tmp_str += re.sub("[a-z0-9]", "", project[1:])
            invalid_list = list(set(tmp_str))
            invalid_list.sort()
            invalid_chars = "".join(str(e) for e in invalid_list)

            print_and_exit(
                "Wrong project name, found invalid characters: {}", invalid_chars
            )

    def check_main_folder(self) -> Optional[str]:
        folder = Path.cwd()
        first_level_error = self.inspect_main_folder(folder)
        # No error raised: the current folder is a valid rapydo root
        if first_level_error is None:
            return None

        # Errors on the current folder, let's verify parents
        num_iterations = 0
        while str(folder) != "/" and num_iterations < 10:
            folder = folder.parent
            num_iterations += 1
            # Errors at this level, let's continue to verify parents
            if self.inspect_main_folder(folder) is not None:
                continue
            # You found a rapydo folder among your parents!
            # Let's suggest to change dir

            # This is ../../etc
            relative_path = "/".join([".."] * num_iterations)

            return (
                "You are not in the main folder, please change your working dir"
                f"\nFound a valid parent folder: {folder}"
                f"\nSuggested command: cd {relative_path}"
            )

        return first_level_error

    def inspect_main_folder(self, folder: Path) -> Optional[str]:
        """
        RAPyDo commands only works on rapydo projects, we want to ensure that
        the current folder have a rapydo-like structure. These checks are based
        on file existence. Further checks are performed in the following steps
        """

        r = git.get_repo(str(folder))
        if r is None or git.get_origin(r) is None:
            return f"""You are not in a git repository
\nPlease note that this command only works from inside a rapydo-like repository
Verify that you are in the right folder, now you are in: {Path.cwd()}
                """

        for fpath in self.expected_main_folders:
            if not folder.joinpath(fpath).is_dir():

                return f"""Folder not found: {fpath}
\nPlease note that this command only works from inside a rapydo-like repository
Verify that you are in the right folder, now you are in: {Path.cwd()}
                    """

        return None

    def inspect_project_folder(self) -> None:

        for fpath in self.expected_folders:
            if not fpath.is_dir():
                print_and_exit(
                    "Project {} is invalid: required folder not found {}",
                    self.project,
                    fpath,
                )

        for fpath in self.expected_files + self.raw_files:
            if not fpath.is_file():
                print_and_exit(
                    "Project {} is invalid: required file not found {}",
                    self.project,
                    fpath,
                )

        for fpath in self.obsolete_files:
            if fpath.exists():
                print_and_exit(
                    "Project {} contains an obsolete file or folder: {}",
                    self.project,
                    fpath,
                )

    # issues/57
    # I'm temporary here... to be decided how to handle me
    reserved_project_names = [
        "abc",
        "attr",
        "base64",
        "celery",
        "click",
        "collections",
        "datetime",
        "dateutil",
        "email",
        "errno",
        "flask",
        "flask_sqlalchemy",
        "authlib",
        "functools",
        "glob",
        "hashlib",
        "hmac",
        "inspect",
        "io",
        "json",
        "jwt",
        "logging",
        "neo4j",
        "neomodel",
        "os",
        "platform",
        "pickle",
        "plumbum",
        "pyotp",
        "pyqrcode",
        "pytz",
        "random",
        "re",
        "smtplib",
        "socket",
        "sqlalchemy",
        "string",
        "submodules",
        "sys",
        "time",
        "test",
        "unittest",
        "werkzeug",
    ]
