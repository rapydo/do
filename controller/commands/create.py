import os
from typing import List

import typer

from controller import PROJECT_DIR, __version__, gitter, log
from controller.app import Application, Configuration
from controller.project import ANGULAR, NO_FRONTEND, Project
from controller.templating import Templating


@Application.app.command(help="Create a new rapydo project")
def create(
    project_name: str = typer.Argument(..., help="Name of your project"),
    auth: str = typer.Option(
        None, "--auth", help="Auth service to enable (sql, neo4j, mongo)"
    ),
    frontend: str = typer.Option(
        None, "--frontend", help="Frontend framework to enable (no, angular)"
    ),
    extend: str = typer.Option(None, "--extend", help="Extend from another project"),
    services: List[str] = typer.Option(
        "",
        "--service",
        "-s",
        help="Service to be enabled (multiple is enabled)",
        autocompletion=Application.autocomplete_service,
    ),
    origin_url: str = typer.Option(
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
):
    Application.controller.controller_init()

    if extend is not None:
        if project_name == extend:
            log.exit("A project cannot extend itself")
        if not PROJECT_DIR.joinpath(extend).is_dir():
            log.exit("Invalid extend value: project {} not found", extend)

    if auth is None:
        log.exit("Missing authentication service, add --auth option")
    if auth not in ["postgres", "mysql", "neo4j", "mongo"]:
        log.exit("Invalid authentication service: {}", auth)

    create_project(
        project_name=project_name,
        auth=auth,
        frontend=frontend,
        services=services,
        extend=extend,
        envs=envs,
        auto=auto,
        force=force,
        force_current=force_current,
        add_optionals=add_optionals,
    )

    log.info("Project {} successfully created", project_name)

    git_repo = gitter.get_repo(".")
    if git_repo is None:
        git_repo = gitter.init(".")

    print("\nYou can now init and start the project:\n")
    current_origin = gitter.get_origin(git_repo)

    if current_origin is None:
        if origin_url is None:  # pragma: no cover
            print("git remote add origin https://your_remote_git/your_project.git")
        else:
            git_repo.create_remote("origin", origin_url)

    print("rapydo init")
    print("rapydo pull")
    print("rapydo start")


def create_project(
    project_name,
    auth,
    frontend,
    services,
    extend,
    envs=None,
    auto=False,
    force=False,
    force_current=False,
    add_optionals=False,
    path=None,
):

    project_scaffold = Project()
    enable_postgres = auth == "postgres" or "postgres" in services
    enable_mysql = auth == "mysql" or "mysql" in services
    enable_neo4j = auth == "neo4j" or "neo4j" in services
    enable_mongo = auth == "mongo" or "mongo" in services
    enable_rabbit = "rabbit" in services
    enable_redis = "redis" in services
    enable_celery = "celery" in services
    enable_pushpin = "pushpin" in services
    enable_ftp = "ftp" in services
    enable_bot = "bot" in services

    if auth == "postgres" or auth == "mysql":
        auth = "sqlalchemy"

    if frontend is None:
        log.exit("Missing frontend framework, add --frontend option")
    if not frontend or frontend == "no":
        frontend = NO_FRONTEND
    if frontend not in [NO_FRONTEND, ANGULAR]:
        log.exit("Invalid frontend framework: {}", frontend)

    if not force_current:
        dirs = os.listdir(".")
        if dirs and dirs != [".git"]:
            log.exit(
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

    if "_" in project_name:
        log.exit("Wrong project name, _ is not a valid character")

    if project_name in project_scaffold.reserved_project_names:
        log.exit("You selected a reserved name, invalid project name: {}", project_name)

    templating = Templating()

    folders = project_scaffold.expected_folders + project_scaffold.data_folders

    if add_optionals:
        folders += project_scaffold.optionals_folders

    for f in folders:
        if f.exists():
            log.debug("Project folder already exists: {}", f)
            continue
        if not auto:
            log.exit("\nmkdir -p {}", f)

        f.mkdir(parents=True, exist_ok=True)

    for f in project_scaffold.suggested_gitkeep:
        f.open("a").close()

    files = project_scaffold.expected_files
    if add_optionals:
        files += project_scaffold.optionals_files
    files += project_scaffold.recommended_files

    if path:
        if path not in files:
            log.exit("Invalid path, cannot upgrade {}", path)
        else:
            files = [path]

    # Add the Kitchen Sink!
    if Configuration.testing and frontend == ANGULAR:
        path = project_scaffold.p_path("frontend", "app", "components", "sink")
        path.mkdir(parents=True, exist_ok=True)

        files += [
            path.joinpath("sink.ts"),
            path.joinpath("sink.html"),
        ]

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
            log.exit(p)


def parse_env_variables(envs):

    if not envs:
        return {}

    env_variables = {}
    for env in envs:
        e = env.split("=")
        if len(e) != 2:
            log.exit("Invalid env {}, expected: K1=V1", env)
        k = e[0].upper()
        v = e[1]
        env_variables[k] = v

    return env_variables
