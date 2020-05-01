import os
import signal
import shutil
from plumbum import local
from controller.arguments import ArgParser
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
        "rapydo create test --auth sql",
        "Missing frontend framework, add --frontend option",
    )

    exec_command(
        capfd,
        "rapydo create test --auth sql --frontend xyz",
        "Invalid frontend framework: xyz",
    )

    exec_command(
        capfd,
        "rapydo create test_celery --auth sql --frontend angular",
        "Wrong project name, _ is not a valid character",
    )

    exec_command(
        capfd,
        "rapydo create celery --auth sql --frontend angular",
        "You selected a reserved name, invalid project name: celery",
    )

    exec_command(
        capfd,
        "rapydo create test --auth sql --frontend no --no-auto",
        "mkdir -p projects",
    )

    exec_command(
        capfd,
        "rapydo create test --auth sql --frontend angular",
        "Project test successfully created",
    )

    exec_command(
        capfd,
        "rapydo create test --auth sql --frontend angular",
        "Current folder is not empty, cannot create a new project here.",
        "Use --current to force the creation here",
    )

    pconf = "projects/test/project_configuration.yaml"
    os.remove(pconf)
    exec_command(
        capfd,
        "rapydo create test --auth sql --frontend no --current --no-auto",
        "Folder projects/test/confs already exists",
        "{f}".format(f=pconf),
    )

    exec_command(
        capfd,
        "rapydo create test --auth sql --frontend angular --current --force",
        "Folder projects/test/confs already exists",
        "Project test successfully created",
    )
    exec_command(
        capfd,
        "rapydo create test --auth sql --frontend angular --current --force",
        "Folder projects/test/confs already exists",
        "A backup of {f} is saved as {f}.bak".format(f=pconf),
        "Project test successfully created",
    )

    exec_command(
        capfd,
        "rapydo create test --auth sql --frontend no --current",
        "Folder projects/test/confs already exists",
        "{f} already exists".format(f=pconf),
        "Project test successfully created",
    )
    exec_command(
        capfd,
        "rapydo create test --auth sql --frontend no --no-auto --current",
        "Folder projects/test/confs already exists",
        "{f} already exists".format(f=pconf),
        "Project test successfully created",
    )

    exec_command(
        capfd,
        "rapydo init",
        "Project initialized",
    )

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

    # Selected a very fast service to speed up tests
    exec_command(
        capfd,
        "rapydo -s rabbit build --core",
        "Core images built",
        "No custom images to build",
    )

    # Skipping main because we are on a fake git repository
    exec_command(
        capfd,
        "rapydo check -i main",
        "Checks completed",
    )

    exec_command(
        capfd,
        "rapydo check -i main --check-permissions",
        "Checks completed",
    )

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
        "rapydo dump",
        "Config dump: docker-compose.yml",
    )

    os.remove(".projectrc")

    command = local["cp"]
    command(["-r", "projects/test", "projects/second"])

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
        "rapydo --project test init",
        "Project initialized",
    )

    shutil.rmtree('data/logs')
    assert not os.path.isdir('data/logs')
    exec_command(
        capfd,
        "rapydo  init",
        "Project initialized",
    )
    assert os.path.isdir('data/logs')
    exec_command(
        capfd,
        "rapydo check -i main --no-git --no-builds",
        "Checks completed",
    )

    exec_command(
        capfd,
        "rapydo verify sqlalchemy",
        'No container found for backend_1'
    )

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

    # Template project is based on sql
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
    exec_command(
        capfd,
        "rapydo logs -s backend --tail 10 --follow",
        "docker-compose command: 'logs'",
        "Stopped by keyboard",
    )

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
        "rapydo: {v}".format(v=__version__),
        "required rapydo: {v}".format(v=__version__),
    )

    exec_command(
        capfd,
        "rapydo volatile backend --command hostname",
        "backend-server",
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
    exec_command(
        capfd,
        "rapydo version",
        "This project is not compatible with rapydo version 0.7.2"
        "Please upgrade rapydo to version {} or modify this project".format(__version__)
    )
