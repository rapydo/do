# -*- coding: utf-8 -*-
import os
from controller import __version__
from controller.project import NO_FRONTEND, ANGULAR  # ANGULARJS, REACT
from controller.templating import Templating
from controller import log


def __call__(args, project, project_scaffold, **kwargs):

    force = args.get("force", False)
    force_current = args.get("current", False)
    auto = not args.get("no_auto", False)
    # to be deprecated
    wrapped = args.get("wrapped", False)
    auth = args.get("auth")
    frontend = args.get("frontend")
    extend = args.get("extend")
    services = args.get("services", "").split(",")

    if auth is None:
        log.exit("Missing authentication service, add --auth option")
    if auth not in ['postgres', 'mysql', 'neo4j', 'mongo']:
        log.exit("Invalid authentication service: {}", auth)

    enable_postgres = auth == 'postgres' or 'postgres' in services
    enable_mysql = auth == 'mysql' or 'mysql' in services
    enable_neo4j = auth == 'neo4j' or 'neo4j' in services
    enable_mongo = auth == 'mongo' or 'mongo' in services
    enable_rabbit = 'rabbit' in services
    enable_redis = 'redis' in services
    enable_irods = 'irods' in services
    enable_celery = 'celery' in services
    enable_pushpin = 'pushpin' in services
    enable_ftp = 'ftp' in services

    if auth == 'postgres' or auth == 'mysql':
        auth = 'sqlalchemy'

    if frontend is None:
        log.exit("Missing frontend framework, add --frontend option")
    if not frontend or frontend == 'no':
        frontend = NO_FRONTEND
    if frontend not in [NO_FRONTEND, ANGULAR]:
        log.exit("Invalid frontend framework: {}", frontend)

    if not force_current:
        dirs = os.listdir(".")
        if len(dirs) > 0 and dirs != ['.git']:
            log.exit(
                "Current folder is not empty, cannot create a new project here." +
                "\nUse --current to force the creation here")

    celery_broker = None  # Keep default value == RABBIT
    celery_backend = None  # Keep default value == RABBIT
    if enable_celery:
        # BROKER SELECTION = rabbit | redis
        if not enable_rabbit and not enable_redis:
            enable_rabbit = True

        if enable_rabbit:
            celery_broker = 'RABBIT'
        elif enable_redis:
            celery_broker = 'REDIS'

        # BACKEND SELECTION = rabbit | redis | mongo
        if not enable_rabbit and not enable_redis and not enable_mongo:
            enable_rabbit = True

        if enable_redis:
            celery_backend = 'REDIS'
        elif enable_mongo:
            celery_backend = 'MONGODB'
        elif enable_rabbit:
            celery_backend = 'RABBIT'

    project_name = args.get("name")

    project_scaffold.load_project_scaffold(project_name, auth, extended=extend)
    if frontend != NO_FRONTEND:
        project_scaffold.load_frontend_scaffold(frontend)

    if "_" in project_name:
        log.exit("Wrong project name, _ is not a valid character")

    if project_name in project_scaffold.reserved_project_names:
        log.exit(
            "You selected a reserved name, invalid project name: {}",
            project_name
        )

    # if gitter.get_local(".") is not None:
    #     log.exit("You are on a git repo, unable to continue")

    templating = Templating()

    folders = \
        project_scaffold.expected_folders + \
        project_scaffold.data_folders
    for f in folders:
        if os.path.exists(f):
            log.info("Folder {} already exists", f)
            continue
        if not auto:
            log.exit("\nmkdir -p {}", f)

        os.makedirs(f)

    for p in project_scaffold.expected_files:
        fname = os.path.basename(p)
        template = templating.get_template(
            fname,
            {
                'version': __version__,
                'project': project,
                'auth_service': auth,
                'enable_postgres': enable_postgres,
                'enable_mysql': enable_mysql,
                'enable_neo4j': enable_neo4j,
                'enable_mongo': enable_mongo,
                'enable_rabbit': enable_rabbit,
                'enable_redis': enable_redis,
                'enable_irods': enable_irods,
                'enable_celery': enable_celery,
                'enable_pushpin': enable_pushpin,
                'enable_ftp': enable_ftp,
                'celery_broker': celery_broker,
                'celery_backend': celery_backend,
                'frontend': frontend,
                'extend': extend,
                'services': services,
                'wrapped': wrapped,
            }
        )

        # automatic creation
        if auto:
            if os.path.exists(p) and not force:
                log.info("{} already exists", p)
            else:
                templating.save_template(p, template, force=force)
            continue

        # manual creation
        if os.path.exists(p):
            log.info("{} already exists", p)
        else:
            print("\n{}".format(template))
            log.exit(p)

    log.info("Project {} successfully created", project_name)
    print("""
You can now init and start the project:

git init
git remote add origin https://your_remote_git/your_project.git
rapydo init
rapydo pull
rapydo start
""")
