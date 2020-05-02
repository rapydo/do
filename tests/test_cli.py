# -*- coding: utf-8 -*-
import os
import signal
import shutil
from git import Repo
from controller.arguments import ArgParser
from controller.dockerizing import Dock
from controller.app import Application
from controller import __version__


class Timeout(Exception):
    pass


def handler(signum, frame):
    raise Timeout("Time is up")


def mock_KeyboardInterrupt(signum, frame):
    raise KeyboardInterrupt("Time is up")


def exec_command(capfd, command, *asserts):

    with capfd.disabled():
        print("\n")
        print("_____________________________________________")
        print(command)
        print("_____________________________________________")

    arguments = ArgParser(args=command.split(" "))

    try:
        Application(arguments)
    # NOTE: docker-compose calls SystemExit at the end of the command...
    except SystemExit:
        pass

    captured = capfd.readouterr()
    # Remove empty lines
    out = [x for x in captured.out.replace('\r', '').split("\n") if x.strip()]
    err = [x for x in captured.err.replace('\r', '').split("\n") if x.strip()]

    with capfd.disabled():
        for o in out:
            print("_ {}".format(o))
        for e in err:
            print("! {}".format(e))

    for a in asserts:
        # Check if the assert is in any line (also as substring) from out or err
        assert a in out + err or any(a in x for x in out + err)

    return out


def test_all(capfd):
    exec_command(
        capfd,
        "rapydo create test",
        "Missing authentication service, add --auth option",
    )

    exec_command(
        capfd,
        "rapydo create test --auth xyz",
        "Invalid authentication service: xyz",
    )

    exec_command(
        capfd,
        "rapydo create test --auth postgres",
        "Missing frontend framework, add --frontend option",
    )

    exec_command(
        capfd,
        "rapydo create test --auth postgres --frontend xyz",
        "Invalid frontend framework: xyz",
    )

    exec_command(
        capfd,
        "rapydo create test_celery --auth postgres --frontend angular",
        "Wrong project name, _ is not a valid character",
    )

    exec_command(
        capfd,
        "rapydo create celery --auth postgres --frontend angular",
        "You selected a reserved name, invalid project name: celery",
    )

    exec_command(
        capfd,
        "rapydo create test --auth postgres --frontend angular --no-auto",
        "mkdir -p projects",
    )

    # exec_command(
    #     capfd,
    #     "rapydo version",
    #     __version__,
    # )

    # Let's create a project
    exec_command(
        capfd,
        "rapydo create test --auth postgres --frontend angular --services rabbit",
        "Project test successfully created",
    )

    exec_command(
        capfd,
        "rapydo create test --auth postgres --frontend angular",
        "Current folder is not empty, cannot create a new project here.",
        "Use --current to force the creation here",
    )

    pconf = "projects/test/project_configuration.yaml"
    os.remove(pconf)
    exec_command(
        capfd,
        "rapydo create test --auth postgres --frontend angular --current --no-auto",
        "Folder projects/test/confs already exists",
        "{f}".format(f=pconf),
    )

    exec_command(
        capfd,
        "rapydo create test --auth postgres --frontend angular --services rabbit --current --force",
        "Folder projects/test/confs already exists",
        "Project test successfully created",
    )
    exec_command(
        capfd,
        "rapydo create test --auth postgres --frontend angular --services rabbit --current --force",
        "Folder projects/test/confs already exists",
        "A backup of {f} is saved as {f}.bak".format(f=pconf),
        "Project test successfully created",
    )

    exec_command(
        capfd,
        "rapydo create test --auth postgres --frontend angular --current",
        "Folder projects/test/confs already exists",
        "{f} already exists".format(f=pconf),
        "Project test successfully created",
    )

    exec_command(
        capfd,
        "rapydo create test --auth postgres --frontend angular --no-auto --current",
        "Folder projects/test/confs already exists",
        "{f} already exists".format(f=pconf),
        "Project test successfully created",
    )

    # Basic initilization
    exec_command(
        capfd,
        "rapydo init",
        "Project initialized",
    )

    # Basic pull
    exec_command(
        capfd,
        "rapydo pull",
        "Base images pulled from docker hub",
    )

    # Skipping main because we are on a fake git repository
    exec_command(
        capfd,
        "rapydo update -i main",
        "All updated",
    )

    # Skipping main because we are on a fake git repository
    exec_command(
        capfd,
        "rapydo check -i main",
        "Checks completed",
    )

    # Verify fs permissions
    exec_command(
        capfd,
        "rapydo check -i main --check-permissions",
        "Checks completed",
    )

    # Some tests with list
    exec_command(
        capfd,
        "rapydo list",
        "Nothing to list, please use rapydo list -h for available options",
    )
    exec_command(
        capfd,
        "rapydo list --env",
        "List env variables:",
        "ACTIVATE_ALCHEMY",
    )
    exec_command(
        capfd,
        "rapydo list --args",
        "List of configured rapydo arguments:",
    )
    exec_command(
        capfd,
        "rapydo list --active-services",
        "List of active services:",
    )
    exec_command(
        capfd,
        "rapydo list --submodules",
        "List of submodules:",
    )

    exec_command(
        capfd,
        "rapydo interfaces XYZ",
        "Container 'XYZui' is not defined",
        "You can use rapydo interfaces list to get available interfaces",
    )
    exec_command(
        capfd,
        "rapydo interfaces list",
        "List of available interfaces:",
        " - mongo",
        " - sqlalchemy",
        " - swagger",
        " - celery",
    )
    exec_command(
        capfd,
        "rapydo interfaces sqlalchemy --port 123 --detach",
        "Launching interface: sqlalchemyui",
        "docker-compose command: 'run'",
    )

    exec_command(
        capfd,
        "rapydo ancestors XYZ",
        "No parent found for XYZ",
    )

    dock = Dock()
    img = dock.images().pop(0)
    # sha256:c1a845de80526fcab136f9fab5f83BLABLABLABLABLA
    img_id = dock.image_info(img).get('Id')
    # => c1a845de8052
    img_id = img_id[7:19]
    exec_command(
        capfd,
        "rapydo ancestors {}".format(img_id),
        "Finding all parents and (grand)+ parents of {}".format(img_id),
    )

    exec_command(
        capfd,
        "rapydo formatter",
        # This is becase no endpoint is implemented in this project...
        "No paths given. Nothing to do",
    )

    exec_command(
        capfd,
        "rapydo formatter --submodule http-api/restapi --folder resources",
        "All done!",
    )

    exec_command(
        capfd,
        "rapydo version",
        "rapydo: \033[1;32m{v}".format(v=__version__),
        "required rapydo: \033[1;32m{v}".format(v=__version__),
    )

    # docker dump
    exec_command(
        capfd,
        "rapydo dump",
        "Config dump: docker-compose.yml",
    )

    # first project is --auth postgres --frontend angular
    # the second one is --auth neo4j --frontend angular
    exec_command(
        capfd,
        "rapydo create first --auth neo4j --frontend no --current",
        "Folder projects already exists",
        "Project first successfully created",
    )
    exec_command(
        capfd,
        "rapydo create second --extend first --auth neo4j --frontend angular --current --services rabbit",
        "Folder projects already exists",
        "Project second successfully created",
    )
    # Add a custom image to extend base rabbit image:

    os.makedirs("projects/second/builds/rabbit")
    fin = open("projects/second/builds/rabbit/Dockerfile", "wt+")
    fin.write("""
FROM rapydo/rabbitmq:{}
# Just a simple command differentiate from the parent
RUN mkdir xyz
""".format(__version__))
    fin.close()

    fin = open("projects/second/confs/commons.yml", "a")
    fin.write("""
services:
  rabbit:
    build: ${PROJECT_DIR}/builds/rabbit
    image: ${COMPOSE_PROJECT_NAME}/rabbit:${RAPYDO_VERSION}

    """)
    fin.close()
    # Test selection with two projects
    os.remove(".projectrc")

    r = Repo(".")
    r.git.add("-A")
    r.git.commit("-a", "-m", "'fake'")

    exec_command(
        capfd,
        "rapydo check -i main --no-git --no-builds",
        "Please add the --project option with one of the following:",
    )

    exec_command(
        capfd,
        "rapydo -p test check -i main --no-git --no-builds",
        "Checks completed",
    )

    # Check invalid and reserved project names
    exec_command(
        capfd,
        "rapydo -p invalid_character check -i main --no-git --no-builds",
        "Wrong project name, _ is not a valid character.",
    )
    exec_command(
        capfd,
        "rapydo -p celery check -i main --no-git --no-builds",
        "You selected a reserved name, invalid project name: celery",
    )
    exec_command(
        capfd,
        "rapydo -p third check -i main --no-git --no-builds",
        "Wrong project third",
        "Select one of the following: ",
    )

    # Test init of data folders
    shutil.rmtree('data/logs')
    assert not os.path.isdir('data/logs')
    # Let's restore .projectrc and data/logs
    exec_command(
        capfd,
        "rapydo --project test init",
        "Project initialized",
    )
    assert os.path.isdir('data/logs')
    exec_command(
        capfd,
        "rapydo check -i main --no-git --no-builds",
        "Checks completed",
    )

    # Test dirty repo
    fin = open("submodules/do/new_file", "wt+")
    fin.write("xyz")
    fin.close()

    fin = open("submodules/build-templates/backend/Dockerfile", "a")
    fin.write("xyz")
    fin.close()
    r = Repo("submodules/build-templates")
    r.git.commit("-a", "-m", "'fake'")

    exec_command(
        capfd,
        "rapydo check -i main",
        "You have unstaged files on do",
        "Untracked files:",
        "submodules/do/new_file",
        "Obsolete image rapydo/backend:{}".format(__version__),
        "built on ",
        " but changed on ",
        "Update it with: rapydo --services backend pull",
    )
    # Init second project to download submodules/frontend (not enabled on test project)
    exec_command(
        capfd,
        "rapydo -p second init",
        "Project initialized",
    )

    # Selected a very fast service to speed up tests
    # Build custom rabbit image in second project from pulled image
    exec_command(
        capfd,
        "rapydo -p second -s rabbit build",
        "Successfully built",
        "Successfully tagged second/rabbit:{}".format(__version__),
        "Custom images built",
    )

    # Rebuild core rabbit image => custom rabbit is now obsolete
    exec_command(
        capfd,
        "rapydo -p test -s rabbit build --core",
        "Core images built",
        "No custom images to build",
    )
    exec_command(
        capfd,
        "rapydo -p second check -i main --no-git",
        "Obsolete image second/rabbit:{}".format(__version__),
        "built on ",
        " that changed on ",
        "Update it with: rapydo --services rabbit pull",
    )

    exec_command(
        capfd,
        "rapydo verify sqlalchemy",
        'No container found for backend_1'
    )

    # Let's start with the stack
    exec_command(
        capfd,
        "rapydo start",
        "docker-compose command: 'up'",
        "Stack started",
    )

    exec_command(
        capfd,
        "rapydo status",
        "docker-compose command: 'ps'",
        # "test_backend_1",
    )

    exec_command(
        capfd,
        "rapydo shell backend --command hostname",
        "backend-server",
    )
    # Testing default users
    exec_command(
        capfd,
        "rapydo shell backend --command whoami",
        "developer",
    )
    exec_command(
        capfd,
        "rapydo shell frontend --command whoami",
        "node",
    )
    # No default user for rabbit container
    exec_command(
        capfd,
        "rapydo shell rabbit --command whoami",
        "root",
    )
    exec_command(
        capfd,
        "rapydo shell postgres --command whoami",
        "postgres",
    )

    exec_command(
        capfd,
        "rapydo scale rabbit",
        "Please specify how to scale: SERVICE=NUM_REPLICA",
        "You can also set a DEFAULT_SCALE_RABBIT variable in your .projectrc file"
    )
    exec_command(
        capfd,
        "rapydo scale rabbit=x",
        "Invalid number of replicas: x",
    )

    exec_command(
        capfd,
        "rapydo scale rabbit=2",
        "Starting test_rabbit_1",
        "Creating test_rabbit_2",
    )

    exec_command(
        capfd,
        "rapydo scale rabbit=1",
        "Stopping and removing test_rabbit_2",
        "Starting test_rabbit_1",
    )

    exec_command(
        capfd,
        "rapydo logs -s backend --tail 10",
        "docker-compose command: 'logs'",
        "backend_1",
    )

    signal.signal(signal.SIGALRM, mock_KeyboardInterrupt)
    signal.alarm(3)
    try:
        exec_command(
            capfd,
            "rapydo logs -s backend --tail 10 --follow",
            "docker-compose command: 'logs'",
            "Stopped by keyboard",
        )
    except Exception as e:
        print(e)

    # Template project is based on sql
    """
    exec_command(
        capfd,
        "rapydo verify neo4j",
        'Service neo4j not detected'
    )
    exec_command(
        capfd,
        "rapydo verify sqlalchemy",
        'Service sqlalchemy is reachable'
    )
    """

    exec_command(
        capfd,
        "rapydo stop",
        "Stack stopped",
    )

    exec_command(
        capfd,
        "rapydo restart",
        "Stack restarted",
    )

    exec_command(
        capfd,
        "rapydo -s backend remove --net",
        "Incompatibile options --networks and --services",
    )

    exec_command(
        capfd,
        "rapydo -s backend remove --all",
        "Incompatibile options --all and --services",
    )

    exec_command(
        capfd,
        "rapydo remove",
        "docker-compose command: 'stop'",
        "Stack removed",
    )

    exec_command(
        capfd,
        "rapydo remove --networks",
        "Stack removed",
    )

    exec_command(
        capfd,
        "rapydo remove --all",
        "Stack removed",
    )

    exec_command(
        capfd,
        "rapydo shell backend --command hostname",
        "No container found for backend_1",
    )

    signal.signal(signal.SIGALRM, handler)
    signal.alarm(3)

    interrupted = False
    try:
        exec_command(
            capfd,
            "rapydo -s backend start --no-detach",
            "REST API backend server is ready to be launched",
        )
    except Timeout:
        interrupted = True
    assert interrupted

    # This is because after start --no-detach the container in still in exited status
    exec_command(
        capfd,
        "rapydo volatile backend --command hostname",
        "Bind for 0.0.0.0:8080 failed: port is already allocated",
    )

    exec_command(
        capfd,
        "rapydo remove --all",
        "Stack removed",
    )

    exec_command(
        capfd,
        "rapydo volatile backend --command hostname",
        "backend-server",
    )

    pconf = "projects/test/project_configuration.yaml"

    exec_command(
        capfd,
        "rapydo --prod check -i main --no-git --no-builds",
        "The following variables are missing in your configuration",
    )

    exec_command(
        capfd,
        "rapydo --prod init -f",
        "Created default .projectrc file",
        "Project initialized",
    )

    exec_command(
        capfd,
        "rapydo --prod -s proxy pull",
        "Base images pulled from docker hub",
    )

    exec_command(
        capfd,
        "rapydo ssl",
        "No container found for proxy_1",
    )
    exec_command(
        capfd,
        "rapydo ssl --volatile",
        "Creating test_certificates-proxy_1",
    )
    exec_command(
        capfd,
        "rapydo ssl --force",
        "No container found for proxy_1",
    )
    exec_command(
        capfd,
        "rapydo ssl --chain-file /file",
        "Invalid chain file (you provided /file)",
    )
    exec_command(
        capfd,
        "rapydo ssl --key-file /file",
        "Invalid chain file (you provided none)",
    )
    exec_command(
        capfd,
        "rapydo ssl --chain-file {f}".format(f=pconf),
        "Invalid key file (you provided none)",
    )
    exec_command(
        capfd,
        "rapydo ssl --chain-file {f} --key-file /file".format(f=pconf),
        "Invalid key file (you provided /file)",
    )
    exec_command(
        capfd,
        "rapydo ssl --chain-file {f} --key-file {f}".format(f=pconf),
        "Unable to automatically perform the requested operation",
        "You can execute the following commands by your-self:",
    )

    exec_command(
        capfd,
        "rapydo dhparam",
        "No container found for proxy_1",
    )

    exec_command(
        capfd,
        "rapydo install --pip --editable auto",
        "--pip and --editable options are not compatible"
    )

    exec_command(
        capfd,
        "rapydo install --user --editable auto",
        "--user and --editable options are not compatible"
    )

    exec_command(
        capfd,
        "rapydo install --editable auto",
    )

    exec_command(
        capfd,
        "rapydo install --user auto",
    )

    # This is the very last command... installing an old version!
    exec_command(
        capfd,
        "rapydo install --pip --user 0.7.2",
    )

    # This test will change the required version
    pconf = "projects/test/project_configuration.yaml"

    # Read and change the content
    fin = open(pconf, "rt")
    data = fin.read()
    data = data.replace("rapydo: {}".format(__version__), 'rapydo: 0.7.0')
    fin.close()
    # Write the new content
    fin = open(pconf, "wt")
    fin.write(data)
    fin.close()

    exec_command(
        capfd,
        "rapydo version",
        "This project is not compatible with rapydo version {}".format(__version__),
        "Please downgrade rapydo to version 0.7.0 or modify this project"
    )

    # Read and change the content
    fin = open(pconf, "rt")
    data = fin.read()
    data = data.replace("rapydo: 0.7.0", 'rapydo: 99.99.99')
    fin.close()
    # Write the new content
    fin = open(pconf, "wt")
    fin.write(data)
    fin.close()

    exec_command(
        capfd,
        "rapydo version",
        "This project is not compatible with rapydo version {}".format(__version__),
        "Please upgrade rapydo to version 99.99.99 or modify this project"
    )

    # Tests from a subfolder
    os.chdir("projects")
    exec_command(
        capfd,
        "rapydo -p second check -i main --no-git --no-builds",
        "You are not in the main folder",
        "Checks completed",
    )
