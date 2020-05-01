import os
# import shutil
from plumbum import local
from controller.arguments import ArgParser
from controller.app import Application
from controller import __version__


class GlobalVars:
    capfd = None
    out_len = 0
    err_len = 0


def check_command(command, *asserts):
    with GlobalVars.capfd.disabled():
        print("_____________________________________________")
        print(command)
        print("_____________________________________________")
    command = command.split(" ")

    arguments = ArgParser(args=command)

    try:
        Application(arguments)
    # NOTE: docker-compose calls SystemExit at the end of the command...
    except SystemExit:
        # print("Command completed")
        pass

    out, err = GlobalVars.capfd.readouterr()
    out = out.replace('\r', '').split("\n")
    err = err.replace('\r', '').split("\n")
    with GlobalVars.capfd.disabled():
        for o in out[GlobalVars.out_len:]:
            if not o:
                continue
            print("\033[92m{}\033[0m".format(o))
        for e in err[GlobalVars.err_len:]:
            if not e:
                continue
            print("\033[91m{}\033[0m".format(e))

    for a in asserts:
        # Only search on newly added lines
        assert a in out[GlobalVars.out_len:] or a in err[GlobalVars.err_len:]

    GlobalVars.out_len = len(out)
    GlobalVars.err_len = len(err)
    return True


def test_all(capfd):

    GlobalVars.capfd = capfd

    check_command(
        "rapydo create test",
        "Missing authentication service, add --auth option"
    )

    check_command(
        "rapydo create test --auth xyz",
        "Invalid authentication service: xyz",
    )

    check_command(
        "rapydo create test --auth sql",
        "Missing frontend framework, add --frontend option",
    )

    check_command(
        "rapydo create test --auth sql --frontend xyz",
        "Invalid frontend framework: xyz",
    )

    check_command(
        "rapydo create test --auth sql --frontend angular",
        "Project test successfully created",
    )

    check_command(
        "rapydo create test --auth sql --frontend angular",
        "Current folder is not empty, cannot create a new project here.",
    )

    check_command(
        "rapydo create test --auth sql --frontend angular --current --force",
        "Project test successfully created",
    )

    # In this case the command should create/modify nothing... to be tested!
    check_command(
        "rapydo create test --auth sql --frontend angular --current",
        "Project test successfully created",
    )

    check_command(
        "rapydo init",
        "Project initialized",
    )

    check_command(
        "rapydo pull",
        "Base images pulled from docker hub",
    )

    check_command(
        "rapydo --prod -s proxy pull",
        "Base images pulled from docker hub",
    )

    # Skipping main because we are on a fake git repository
    check_command(
        "rapydo update -i main",
        "All updated",
    )

    # Selected a very fast service to speed up tests
    check_command(
        "rapydo -s rabbit build --core",
        "Core images built",
        "No custom images to build",
    )

    # Skipping main because we are on a fake git repository
    check_command(
        "rapydo check -i main",
        "Checks completed",
    )

    check_command(
        "rapydo check -i main --check-permissions",
        "Checks completed",
    )

    check_command(
        "rapydo list --env",
        "List env variables:",
    )

    check_command(
        "rapydo list --args",
        "List of configured rapydo arguments:",
    )

    check_command(
        "rapydo list --active-services",
        "List of active services:",
    )

    check_command(
        "rapydo list --submodules",
        "List of submodules:",
    )

    check_command(
        "rapydo dump",
        "Config dump: docker-compose.yml",
    )

    os.remove(".projectrc")

    command = local["cp"]
    command(["-r", "projects/test", "projects/second"])

    check_command(
        "rapydo check -i main --no-git --no-builds",
        "Please add the --project option with one of the following:",
    )

    check_command(
        "rapydo -p test check -i main --no-git --no-builds",
        "Checks completed",
    )

    check_command(
        "rapydo -p invalid_character check -i main --no-git --no-builds",
        "Wrong project name, _ is not a valid character.",
    )

    check_command(
        "rapydo -p celery check -i main --no-git --no-builds",
        "You selected a reserved name, invalid project name: celery",
    )

    check_command(
        "rapydo --project test init",
        "Project initialized",
    )

    check_command(
        "rapydo check -i main --no-git --no-builds",
        "Checks completed",
    )

    check_command(
        "rapydo start",
        "docker-compose command: 'up'",
        "Stack started",
    )

    check_command(
        "rapydo status",
        "docker-compose command: 'ps'",
        "test_backend_1",
    )

    check_command(
        "rapydo shell backend --command hostname",
        "backend-server",
    )

    # Template project is based on sql
    check_command(
        "rapydo verify neo4j",
        'Service "neo4j" was NOT detected',
    )

    check_command(
        "rapydo verify postgres",
        "Service postgres is reachable",
    )

    check_command(
        "rapydo scale rabbit=2",
        "Starting test_rabbit_1",
        "Creating test_rabbit_2",
    )

    check_command(
        "rapydo scale rabbit=1",
        "Stopping and removing test_rabbit_2",
        "Starting test_rabbit_1",
    )

    check_command(
        "rapydo logs",
        "docker-compose command: 'logs'"
    )

    check_command(
        "rapydo stop",
        "Stack stopped",
    )

    check_command(
        "rapydo restart",
        "Stack restarted",
    )

    check_command(
        "rapydo remove",
        "docker-compose command: 'stop'",
        "Stack removed",
    )

    check_command(
        "rapydo remove --networks",
        "Stack removed",
    )

    check_command(
        "rapydo remove --all",
        "Stack removed",
    )

    check_command(
        "rapydo shell backend --command hostname",
        "No container found for backend_1",
    )

    check_command(
        "rapydo interfaces sqlalchemy --port 123 --detach",
        "Launching interface: sqlalchemyui",
        "docker-compose command: 'run'",
    )

    check_command(
        "rapydo ancestors XYZ",
        "No parent found for XYZ",
    )

    check_command(
        "rapydo ssl",
        "No container found for proxy_1",
    )
    check_command(
        "rapydo ssl --volatile",
        "Creating test_certificates-proxy_1"
    )
    check_command(
        "rapydo ssl --force",
        "No container found for proxy_1",
    )
    check_command(
        "rapydo ssl --chain-file /file",
        "Invalid chain file (you provided /file)",
    )
    check_command(
        "rapydo ssl --key-file /file",
        "Invalid chain file (you provided none)",
    )
    f = "projects/test/project_configuration.yaml"
    check_command(
        "rapydo ssl --chain-file {}".format(f),
        "Invalid key file (you provided none)",
    )
    check_command(
        "rapydo ssl --chain-file {} --key-file /file".format(f),
        "Invalid key file (you provided /file)",
    )
    check_command(
        "rapydo ssl --chain-file {f} --key-file {f}".format(f=f),
        "Unable to automatically perform the requested operation",
        "You can execute the following commands by your-self:",
    )

    check_command(
        "rapydo dhparam",
        "No container found for proxy_1",
    )

    check_command(
        "rapydo formatter",
        "All done!",
        # This is because no endpoint is implemented in this project...
        "No paths given. Nothing to do"
    )

    check_command(
        "rapydo formatter --submodule http-api/restapi --folder resources",
        "All done!",
    )

    check_command(
        "rapydo version",
        __version__,
    )

    check_command(
        "rapydo volatile backend --command hostname",
        "backend-server",
    )

    check_command(
        "rapydo install --editable auto",
    )
    check_command(
        "rapydo install --user auto",
    )
    check_command(
        "rapydo install auto",
    )
