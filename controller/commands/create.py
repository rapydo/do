import os

from controller import PROJECT_DIR, __version__, gitter, log
from controller.project import ANGULAR, NO_FRONTEND, Project  # REACT
from controller.templating import Templating


def parse_env_variables(envs):

    env_variables = {}
    if not envs:
        return env_variables

    for e in envs.split(","):
        e = e.split("=")
        if len(e) != 2:
            log.exit("Invalid envs format, expected: K1=V1,K2=V2,...")
        k = e[0].upper()
        v = e[1]
        env_variables[k] = v

    return env_variables


def __call__(args, **kwargs):

    project_name = args.get("name")
    force = args.get("force", False)
    force_current = args.get("current", False)
    auto = not args.get("no_auto", False)
    auth = args.get("auth")
    frontend = args.get("frontend")
    extend = args.get("extend")
    origin_url = args.get("origin_url")
    services = args.get("services", "").split(",")
    envs = args.get("env")
    add_optionals = args.get("add_optionals", False)

    if extend is not None:
        if project_name == extend:
            log.exit("A project cannot extend itself")
        if not os.path.isdir(os.path.join(PROJECT_DIR, extend)):
            log.exit("Invalid extend value: project {} not found", extend)

    if auth is None:
        log.exit("Missing authentication service, add --auth option")
    if auth not in ["postgres", "mysql", "neo4j", "mongo"]:
        log.exit("Invalid authentication service: {}", auth)

    create(
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
        if origin_url is None:  # pragma: yes cover
            print("git remote add origin https://your_remote_git/your_project.git")
        else:
            git_repo.create_remote("origin", origin_url)

    print("rapydo init")
    print("rapydo pull")
    print("rapydo start")


def create(
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
    enable_irods = "irods" in services or "icat" in services
    enable_celery = "celery" in services
    enable_pushpin = "pushpin" in services
    enable_ftp = "ftp" in services

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

    project_scaffold.load_project_scaffold(project_name, auth)
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
        if os.path.exists(f):
            log.debug("Project folder already exists: {}", f)
            continue
        if not auto:
            log.exit("\nmkdir -p {}", f)

        os.makedirs(f)

    files = project_scaffold.expected_files
    if add_optionals:
        files += project_scaffold.optionals_files
    files += project_scaffold.recommended_files

    if path:
        if path not in files:
            log.exit("Invalid path, cannot upgrade {}", path)
        else:
            files = [path]

    for p in files:

        fname = os.path.basename(p)
        template = templating.get_template(
            fname,
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
                "enable_irods": enable_irods,
                "enable_celery": enable_celery,
                "enable_pushpin": enable_pushpin,
                "enable_ftp": enable_ftp,
                "celery_broker": celery_broker,
                "celery_backend": celery_backend,
                "frontend": frontend,
                "extend": extend,
                "services": services,
                "env_variables": env_variables,
            },
        )

        # automatic creation
        if auto:
            if os.path.exists(p) and not force:
                log.info("Project file already exists: {}", p)
            else:
                templating.save_template(p, template, force=force)
            continue

        # manual creation
        if os.path.exists(p):
            log.info("Project file already exists: {}", p)
        else:
            print("\n{}".format(template))
            log.exit(p)
