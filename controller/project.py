import os

from controller import PROJECT_DIR, gitter, log

NO_FRONTEND = "nofrontend"
ANGULAR = "angular"
REACT = "react"


# move here all checks on project (required files, creation functions, templating, etc)
class Project:
    def __init__(self):
        self.expected_main_folders = [PROJECT_DIR, "data", "submodules"]
        # Will be verifed by check and added by create
        self.expected_folders = []
        self.expected_files = []
        # Not verified, added by create if --add-optionals
        self.optionals_folders = []
        self.optionals_files = []
        # Now verified by create, added by create if missing
        self.recommended_files = []
        # Created in data if missing
        self.data_folders = []
        self.data_files = []
        # check will raise an errore if these files will be found
        self.obsolete_files = []

    def p_path(self, *args):
        return os.path.join(PROJECT_DIR, self.project, *args)

    def load_project_scaffold(self, project, auth):
        self.project = project
        self.expected_folders.extend(self.expected_main_folders)
        self.expected_folders.append(self.p_path("confs"))
        self.expected_folders.append(self.p_path("builds"))
        self.expected_folders.append(self.p_path("backend"))
        self.expected_folders.append(self.p_path("backend", "apis"))
        self.expected_folders.append(self.p_path("backend", "models"))
        self.expected_folders.append(self.p_path("backend", "tasks"))
        self.expected_folders.append(self.p_path("backend", "tests"))
        self.expected_folders.append(self.p_path("backend", "initialization"))

        self.expected_files.append(self.p_path("project_configuration.yaml"))
        self.expected_files.append(self.p_path("confs", "commons.yml"))
        self.expected_files.append(self.p_path("confs", "development.yml"))
        self.expected_files.append(self.p_path("confs", "production.yml"))
        self.expected_files.append(
            self.p_path("backend", "initialization", "initialization.py")
        )
        self.expected_files.append(".gitignore")

        if auth is not None:
            model_file = "{}.py".format(auth)
            self.expected_files.append(self.p_path("backend", "models", model_file))

        self.optionals_folders.append(self.p_path("backend", "models", "emails"))
        self.optionals_files.append(self.p_path("backend", "apis", "profile.py"))
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

        self.recommended_files.append(".pre-commit-config.yaml")
        self.recommended_files.append(".isort.cfg")
        self.recommended_files.append("pyproject.toml")
        self.recommended_files.append(".flake8")
        self.data_folders.extend([os.path.join("data", "logs")])

        # Deprecated since 0.7.1
        self.obsolete_files.append(self.p_path("confs", "debug.yml"))
        # Deprecated since 0.7.4
        self.obsolete_files.append(os.path.join("submodules", "rapydo-confs"))

        return True

    def load_frontend_scaffold(self, frontend):
        self.frontend = frontend

        if self.frontend is None or self.frontend == NO_FRONTEND:
            log.debug("No frontend framework enabled")
            return False

        self.expected_folders.append(self.p_path("frontend"))

        if self.frontend == ANGULAR:
            self.expected_folders.extend(
                [
                    self.p_path("frontend", "app"),
                    self.p_path("frontend", "css"),
                    self.p_path("frontend", "integration"),
                ]
            )

            self.expected_files.extend(
                [
                    self.p_path("frontend", "package.json"),
                    self.p_path("frontend", "app", "custom.project.options.ts"),
                    self.p_path("frontend", "app", "custom.module.ts"),
                    self.p_path("frontend", "app", "custom.navbar.ts"),
                    self.p_path("frontend", "app", "custom.footer.ts"),
                    self.p_path("frontend", "app", "custom.profile.ts"),
                    self.p_path("frontend", "css", "style.css"),
                    self.p_path("frontend", "app", "custom.navbar.links.html"),
                    self.p_path("frontend", "app", "custom.navbar.brand.html"),
                    self.p_path("frontend", "app", "custom.footer.html"),
                    self.p_path("frontend", "app", "custom.profile.html"),
                ]
            )

            data_dir = os.path.join("data", self.project, "frontend")
            self.data_folders.extend(
                [
                    data_dir,
                    os.path.join(data_dir, "app"),
                    os.path.join(data_dir, "courtesy"),
                    os.path.join(data_dir, "e2e"),
                    os.path.join(data_dir, "node_modules"),
                    os.path.join("data", self.project, "karma"),
                    os.path.join("data", self.project, "cypress"),
                ]
            )

            self.data_files.extend(
                [
                    os.path.join(data_dir, "angular.json"),
                    os.path.join(data_dir, "browserslist"),
                    os.path.join(data_dir, "karma.conf.js"),
                    os.path.join(data_dir, "package.json"),
                    os.path.join(data_dir, "polyfills.ts"),
                    os.path.join(data_dir, "tsconfig.app.json"),
                    os.path.join(data_dir, "tsconfig.json"),
                    os.path.join(data_dir, "tsconfig.spec.json"),
                    os.path.join(data_dir, "tslint.json"),
                    os.path.join(data_dir, "cypress.json"),
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
                ]
            )

        return True

    @staticmethod
    def get_project(project):

        projects = os.listdir(PROJECT_DIR)

        if project is None:

            if len(projects) == 0:
                log.exit("No project found ({} folder is empty?)", PROJECT_DIR)

            if len(projects) > 1:
                log.exit(
                    "Multiple projects found, "
                    "please use --project to specify one of the following: {}",
                    ",".join(projects),
                )
            project = projects.pop()

        elif project not in projects:
            log.exit(
                "Wrong project {}\nSelect one of the following: {}\n".format(
                    project, ", ".join(projects)
                )
            )

        ABS_PROJECT_PATH = os.path.join(PROJECT_DIR, project)
        return project, ABS_PROJECT_PATH

    def find_main_folder(self):
        first_level_error = self.inspect_main_folder()
        if first_level_error is None:
            return first_level_error
        cwd = os.getcwd()
        num_iterations = 0
        while cwd != "/" and num_iterations < 10:
            num_iterations += 1
            # TODO: use utils.path here
            os.chdir("..")
            cwd = os.getcwd()
            if self.inspect_main_folder() is not None:
                continue
            # You found a rapydo folder among your parents!
            log.warning(
                "You are not in the main folder, working dir changed to {}", cwd,
            )
            first_level_error = None
            break
        return first_level_error

    def inspect_main_folder(self):
        """
        RAPyDo commands only works on rapydo projects, we want to ensure that
        the current folder have a rapydo-like structure. These checks are based
        on file existence. Further checks are performed in the following steps
        """

        r = gitter.get_repo(".")
        if r is None or gitter.get_origin(r) is None:
            return """You are not in a git repository
\nPlease note that this command only works from inside a rapydo-like repository
Verify that you are in the right folder, now you are in: {}
                """.format(
                os.getcwd()
            )

        for fpath in self.expected_main_folders:
            if not os.path.exists(fpath) or not os.path.isdir(fpath):

                return """Folder not found: {}
\nPlease note that this command only works from inside a rapydo-like repository
Verify that you are in the right folder, now you are in: {}
                    """.format(
                    fpath, os.getcwd()
                )

        return None

    def inspect_project_folder(self):

        for fpath in self.expected_folders:
            # fpath = os.path.join(PROJECT_DIR, self.project, fname)
            if not os.path.exists(fpath) or not os.path.isdir(fpath):
                log.exit(
                    "Project {} is invalid: required folder not found {}",
                    self.project,
                    fpath,
                )

        for fpath in self.expected_files:
            # fpath = os.path.join(PROJECT_DIR, self.project, fname)
            if not os.path.exists(fpath) or not os.path.isfile(fpath):
                log.exit(
                    "Project {} is invalid: required file not found {}",
                    self.project,
                    fpath,
                )

        for fpath in self.obsolete_files:
            # fpath = os.path.join(PROJECT_DIR, self.project, fname)
            if os.path.exists(fpath):
                log.exit(
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
        "bravado_core",
        "celery",
        "click",
        "collections",
        "datetime",
        "dateutil",
        "email",
        "errno",
        "flask",
        "flask_restful",
        "flask_sqlalchemy",
        "authlib",
        "functools",
        "glob",
        "hashlib",
        "hmac",
        "inspect",
        "io",
        "irods",
        "iRODSPickleSession",
        "json",
        "jwt",
        "logging",
        "neo4j",
        "neomodel",
        "os",
        "platform",
        "pickle",
        "plumbum",
        "pymodm",
        "pymongo",
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
