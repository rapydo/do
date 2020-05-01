import os
# import shutil
from plumbum import local
from controller.arguments import ArgParser
from controller.app import Application
from controller import __version__


def exec_command(capfd, command, *asserts):

    with capfd.disabled():
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
        assert any(a in x for x in out + err)

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
        "rapydo create test --auth sql --frontend angular",
        "Project test successfully created",
    )

    exec_command(
        capfd,
        "rapydo create test --auth sql --frontend angular",
        "Current folder is not empty, cannot create a new project here.",
    )

    exec_command(
        capfd,
        "rapydo create test --auth sql --frontend angular --current --force",
        "Project test successfully created",
    )

    # In this case the command should create/modify nothing... to be tested!
    exec_command(
        capfd,
        "rapydo create test --auth sql --frontend angular --current",
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
        "rapydo list --env",
        "List env variables:",
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

    exec_command(
        capfd,
        "rapydo check -i main --no-git --no-builds",
        "Checks completed",
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
        'Service "neo4j" was NOT detected'
    )

    exec_command(
        capfd,
        "rapydo verify postgres",
        'Service "postgres" is reachable'
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
        "rapydo logs",
        "docker-compose command: 'logs'",
        "test_backend_1",
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
        "rapydo ssl",
        "No container found for proxy_1",
    )
    # You should pull the proxy before testing --volatile
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
    f = "projects/test/project_configuration.yaml"
    exec_command(
        capfd,
        "rapydo ssl --chain-file {}".format(f),
        "Invalid key file (you provided none)",
    )
    exec_command(
        capfd,
        "rapydo ssl --chain-file {} --key-file /file".format(f),
        "Invalid key file (you provided /file)",
    )
    exec_command(
        capfd,
        "rapydo ssl --chain-file {f} --key-file {f}".format(f=f),
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
        "All udone!",
        # This is becase no endpoint is implemented in this project...
        "No paths given",
    )

    exec_command(
        capfd,
        "rapydo formatter --submodule http-api/restapi --folder resources",
        "All done!",
    )

    exec_command(
        capfd,
        "rapydo version",
        __version__,
    )

    exec_command(
        capfd,
        "rapydo volatile backend --command hostname",
        "backend-server",
    )

    exec_command(
        capfd,
        "rapydo install --editable auto",
    )

    exec_command(
        capfd,
        "rapydo install --user auto",
    )
    exec_command(
        capfd,
        "rapydo install auto",
    )
