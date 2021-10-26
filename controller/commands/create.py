import os
import shutil
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional

import typer

from controller import PROJECT_DIR, __version__, log, print_and_exit
from controller.app import Application, Configuration
from controller.project import NO_AUTHENTICATION, NO_FRONTEND, Project
from controller.templating import Templating
from controller.utilities import git


class AuthTypes(str, Enum):
    no = "no"
    postgres = "postgres"
    mysql = "mysql"
    neo4j = "neo4j"
    mongo = "mongo"


class ServiceTypes(str, Enum):
    postgres = "postgres"
    mysql = "mysql"
    neo4j = "neo4j"
    mongo = "mongo"
    rabbit = "rabbit"
    redis = "redis"
    celery = "celery"
    flower = "flower"
    fail2ban = "fail2ban"
    pushpin = "pushpin"
    ftp = "ftp"
    bot = "bot"


class FrontendTypes(str, Enum):
    no = "no"
    angular = "angular"


@Application.app.command(help="Create a new rapydo project")
def create(
    project_name: str = typer.Argument(..., help="Name of your project"),
    auth: AuthTypes = typer.Option(..., "--auth", help="Auth service to enable"),
    frontend: FrontendTypes = typer.Option(
        ..., "--frontend", help="Frontend framework to enable"
    ),
    extend: str = typer.Option(None, "--extend", help="Extend from another project"),
    services: List[ServiceTypes] = typer.Option(
        [],
        "--service",
        "-s",
        help="Service to be enabled (multiple is enabled)",
        shell_complete=Application.autocomplete_service,
    ),
    origin_url: Optional[str] = typer.Option(
        None, "--origin-url", help="Set the git origin url for the project"
    ),
    envs: List[str] = typer.Option(
        None,
        "--env",
        "-e",
        help="Command separated list of ENV=VALUE to be added in project_configuration",
    ),
    force_current: bool = typer.Option(
        False,
        "--current",
        help="Force creation in current folder",
        show_default=False,
    ),
    force: bool = typer.Option(
        False,
        "--force",
        help="Force files overwriting",
        show_default=False,
    ),
    auto: bool = typer.Option(
        True,
        "--no-auto",
        help="Disable automatic project creation",
        show_default=False,
    ),
    add_optionals: bool = typer.Option(
        False,
        "--add-optionals",
        help="Include all optionals files (html templates and customizers)",
        show_default=False,
    ),
) -> None:

    Application.print_command(
        Application.serialize_parameter("--auth", auth),
        Application.serialize_parameter("--frontend", frontend),
        Application.serialize_parameter("--extend", extend, IF=extend),
        Application.serialize_parameter("--service", services),
        Application.serialize_parameter("--origin-url", origin_url, IF=origin_url),
        Application.serialize_parameter("--env", envs),
        Application.serialize_parameter("--current", force_current, IF=force_current),
        Application.serialize_parameter("--force", force, IF=force),
        Application.serialize_parameter("--auto", auto, IF=auto),
        Application.serialize_parameter("--add-optionals", add_optionals),
        Application.serialize_parameter("", project_name),
    )

    Application.get_controller().controller_init()

    if extend is not None:
        if project_name == extend:
            print_and_exit("A project cannot extend itself")

        if not PROJECT_DIR.joinpath(extend).is_dir():
            print_and_exit("Invalid extend value: project {} not found", extend)

    services_list: List[str] = [service.value for service in services]
    create_project(
        project_name=project_name,
        auth=auth.value,
        frontend=frontend.value,
        services=services_list,
        extend=extend,
        envs=envs,
        auto=auto,
        force=force,
        force_current=force_current,
        add_optionals=add_optionals,
    )

    log.info("Project {} successfully created", project_name)

    git_repo = git.get_repo(".")
    if git_repo is None:
        git_repo = git.init(".")

    print("\nYou can now init and start the project:\n")
    current_origin = git.get_origin(git_repo)

    if current_origin is None:
        if origin_url is None:  # pragma: no cover
            print("git remote add origin https://your_remote_git/your_project.git")
        else:
            git_repo.create_remote("origin", origin_url)

    print("rapydo init")
    print("rapydo pull")
    print("rapydo start")


def create_project(
    project_name: str,
    auth: str,
    frontend: str,
    services: List[str],
    extend: Optional[str],
    envs: Optional[List[str]] = None,
    auto: bool = False,
    force: bool = False,
    force_current: bool = False,
    add_optionals: bool = False,
    path: Path = None,
) -> None:

    project_scaffold = Project()
    enable_postgres = auth == "postgres" or "postgres" in services
    enable_mysql = auth == "mysql" or "mysql" in services
    enable_neo4j = auth == "neo4j" or "neo4j" in services
    enable_mongo = auth == "mongo" or "mongo" in services
    enable_rabbit = "rabbit" in services
    enable_redis = "redis" in services
    enable_celery = "celery" in services
    enable_flower = "flower" in services
    enable_fail2ban = "fail2ban" in services
    enable_pushpin = "pushpin" in services
    enable_ftp = "ftp" in services
    enable_bot = "bot" in services

    if auth == "postgres" or auth == "mysql":
        auth = "sqlalchemy"

    if auth == "no":
        auth = NO_AUTHENTICATION

    if frontend == "no":
        frontend = NO_FRONTEND

    if not force_current:
        dirs = os.listdir(".")
        if dirs and dirs != [".git"]:
            print_and_exit(
                "Current folder is not empty, cannot create a new project here.\n"
                "Found: {}\n"
                "Use --current to force the creation here",
                ", ".join(dirs[0:3]),  # add first 3 files/folders found
            )

    celery_broker = None  # Keep default value == RABBIT
    celery_backend = None  # Keep default value == RABBIT
    if enable_celery:

        if enable_rabbit:
            celery_broker = "RABBIT"
        elif enable_redis:
            celery_broker = "REDIS"
        else:
            celery_broker = "RABBIT"

        if enable_redis:
            celery_backend = "REDIS"
        elif enable_mongo:
            celery_backend = "MONGODB"
        else:
            celery_backend = "RABBIT"

        enable_rabbit = celery_broker == "RABBIT" or celery_backend == "RABBIT"

    env_variables = parse_env_variables(envs)

    project_scaffold.load_project_scaffold(project_name, auth, services)
    if frontend != NO_FRONTEND:
        project_scaffold.load_frontend_scaffold(frontend)

    # In case of errors this function will exit
    project_scaffold.check_invalid_characters(project_name)

    if project_name in project_scaffold.reserved_project_names:
        print_and_exit(
            "You selected a reserved name, invalid project name: {}", project_name
        )

    templating = Templating()

    folders = project_scaffold.expected_folders + project_scaffold.data_folders

    if add_optionals:
        folders += project_scaffold.optionals_folders

    for f in folders:
        if f.exists():
            log.debug("Project folder already exists: {}", f)
            continue
        if not auto:
            print_and_exit("\nmkdir -p {}", f)

        f.mkdir(parents=True, exist_ok=True)

    for f in project_scaffold.suggested_gitkeep:
        f.open("a").close()

    files = project_scaffold.expected_files
    if add_optionals:
        files += project_scaffold.optionals_files

    if path:
        if path not in files:
            print_and_exit("Invalid path, cannot upgrade {}", path)
        else:
            files = [path]

    for p in files:

        template = templating.get_template(
            p.name,
            {
                "version": __version__,
                "project": project_name,
                "auth_service": auth,
                "enable_postgres": enable_postgres,
                "enable_mysql": enable_mysql,
                "enable_neo4j": enable_neo4j,
                "enable_mongo": enable_mongo,
                "enable_rabbit": enable_rabbit,
                "enable_redis": enable_redis,
                "enable_celery": enable_celery,
                "enable_flower": enable_flower,
                "enable_fail2ban": enable_fail2ban,
                "enable_pushpin": enable_pushpin,
                "enable_ftp": enable_ftp,
                "enable_bot": enable_bot,
                "celery_broker": celery_broker,
                "celery_backend": celery_backend,
                "frontend": frontend,
                "testing": Configuration.testing,
                "extend": extend,
                "services": services,
                "env_variables": env_variables,
            },
        )

        # automatic creation
        if auto:
            if p.exists() and not force:
                log.info("Project file already exists: {}", p)
            else:
                templating.save_template(p, template, force=force)
            continue

        # manual creation
        if p.exists():
            log.info("Project file already exists: {}", p)
        else:
            print(f"\n{template}")
            print_and_exit(str(p))

    if not path:
        for p in project_scaffold.raw_files:
            # automatic creation
            if auto:
                if p.exists() and not force:
                    log.info("Project file already exists: {}", p)
                else:
                    shutil.copyfile(templating.template_dir.joinpath(p.name), p)
                continue

            # manual creation
            if p.exists():
                log.info("Project file already exists: {}", p)
            else:
                # print(f"Missing file: {p}")
                print_and_exit("File is missing: {}", p)


def parse_env_variables(envs: Optional[List[str]]) -> Dict[str, str]:

    if not envs:
        return {}

    env_variables: Dict[str, str] = {}
    for env in envs:
        e = env.split("=")
        if len(e) != 2:
            print_and_exit("Invalid env {}, expected: K1=V1", env)
        k = e[0].upper()
        v = e[1]
        env_variables[k] = v

    return env_variables
