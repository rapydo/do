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
    auth = args.get("auth")
    frontend = args.get("frontend")
    extend = args.get("extend")

    if auth is None:
        log.exit("Missing authentication service, add --auth option")
    if auth not in ['sql', 'neo4j', 'mongo']:
        log.exit("Invalid authentication service: {}", auth)

    if auth == 'sql':
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

    project_name = args.get("name")

    project_scaffold.load_project_scaffold(project_name, auth)
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

    # if os.path.exists(project_name):
    #     log.exit("{} folder already exists, unable to continue", project_name)

    # os.makedirs(project_name)

    # if not os.path.exists(project_name):
    #     log.exit("Errors creating {} folder", project_name)

    templating = Templating()

    # 2 - cd project_name

    # 3 - git init

    # 4 - create folders
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

    # 5 - files
    for p in project_scaffold.expected_files:
        fname = os.path.basename(p)
        template = templating.get_template(
            fname,
            {
                'version': __version__,
                'project': project,
                'auth_service': auth,
                'enable_sql': auth == 'sqlalchemy',
                'enable_neo4j': auth == 'neo4j',
                'enable_mongo': auth == 'mongo',
                'frontend': frontend,
                'extend': extend,
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