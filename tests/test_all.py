import os
# import shutil
from plumbum import local
from controller.arguments import ArgParser
from controller.app import Application
from controller import __version__


class GlobalCapfd:
    capfd = None


def check_command(command, *asserts):
    print("*********************************************")
    print(command)
    print("_____________________________________________")
    command = command.split(" ")

    arguments = ArgParser(args=command)

    try:
        Application(arguments)
    # NOTE: docker-compose calls SystemExit at the end of the command...
    except SystemExit:
        print("*********************************************")

    out, err = GlobalCapfd.capfd.readouterr()
    out = out.replace('\r', '').split("\n")
    err = err.replace('\r', '').split("\n")
    print(len(out))
    print(len(err))
    for o in out:
        if not o:
            continue
        print("OUT: {}".format(o))
    for e in err:
        if not e:
            continue
        print("ERR: {}".format(e))

    for a in asserts:
        assert a in out or a in err

    return True

# DEBUG 1 = out + err
# DEBUG 1 = GlobalCapfd
# DEBUG 1 = *args


def test_all(capfd):

    GlobalCapfd.capfd = capfd

    check_command(
        "rapydo create test",
        "Missing authentication service, add --auth option"
    )

    out = check_command("rapydo create test --auth xyz")
    assert "Invalid authentication service: xyz" in out

    out = check_command("rapydo create test --auth sql")
    assert "Missing frontend framework, add --frontend option" in out

    out = check_command("rapydo create test --auth sql --frontend xyz")
    assert "Invalid frontend framework: xyz" in out

    out = check_command("rapydo create test --auth sql --frontend angular")
    assert "Project test successfully created" in out

    out = check_command("rapydo create test --auth sql --frontend angular")
    assert "Current folder is not empty, cannot create a new project here." in out

    out = check_command("rapydo create test --auth sql --frontend angular --current --force")
    assert "Project test successfully created" in out

    # In this case the command should create/modify nothing... to be tested!
    out = check_command("rapydo create test --auth sql --frontend angular --current")
    assert "Project test successfully created" in out

    out = check_command("rapydo init")
    assert "Project initialized" in out

    out = check_command("rapydo pull")
    assert "Base images pulled from docker hub" in out

    # out = check_command("rapydo --prod -s proxy pull")
    # assert "Base images pulled from docker hub" in out

    # Skipping main because we are on a fake git repository
    out = check_command("rapydo update -i main")
    assert "All updated" in out

    # Selected a very fast service to speed up tests
    out = check_command("rapydo -s rabbit build --core")
    assert "Core images built" in out
    assert "No custom images to build" in out

    # Skipping main because we are on a fake git repository
    out = check_command("rapydo check -i main")
    assert "Checks completed" in out

    out = check_command("rapydo check -i main --check-permissions")
    assert "Checks completed" in out

    out = check_command("rapydo list --env")
    assert "List env variables:" in out

    out = check_command("rapydo list --args")
    assert "List of configured rapydo arguments:" in out

    out = check_command("rapydo list --active-services")
    assert "List of active services:" in out

    out = check_command("rapydo list --submodules")
    assert "List of submodules:" in out

    out = check_command("rapydo dump")
    assert "Config dump: docker-compose.yml" in out

    os.remove(".projectrc")

    command = local["cp"]
    command(["-r", "projects/test", "projects/second"])

    out = check_command("rapydo check -i main --no-git --no-builds")
    assert "Please add the --project option with one of the following:" in out

    out = check_command("rapydo -p test check -i main --no-git --no-builds")
    assert "Checks completed" in out

    out = check_command("rapydo -p invalid_character check -i main --no-git --no-builds")
    assert "Wrong project name, _ is not a valid character." in out

    out = check_command("rapydo -p celery check -i main --no-git --no-builds")
    assert "You selected a reserved name, invalid project name: celery" in out

    out = check_command("rapydo --project test init")
    assert "Project initialized" in out

    out = check_command("rapydo check -i main --no-git --no-builds")
    assert "Checks completed" in out

    out = check_command("rapydo start")
    assert "docker-compose command: 'up'" in out
    assert "Stack started" in out

    out = check_command("rapydo status")
    assert "docker-compose command: 'ps'" in out
    # assert "test_backend_1" in out

    out = check_command("rapydo shell backend --command hostname")
    assert "backend-server" in out

    # Template project is based on sql
    check_command("rapydo verify neo4j")
    # This output is not captured, since it is produced by the backend
    # assert 'Service "neo4j" was NOT detected' in out

    check_command("rapydo verify postgres")
    # This output is not capture, since it is produced by the backend
    # assert "Service postgres is reachable" in out

    out = check_command("rapydo scale rabbit=2")
    # assert "Starting test_rabbit_1" in out
    # assert "Creating test_rabbit_2" in out

    out = check_command("rapydo scale rabbit=1")
    # assert "Stopping and removing test_rabbit_2" in out
    # assert "Starting test_rabbit_1" in out

    check_command("rapydo logs")
    # FIXME: how is possible that this message is not found??
    # assert "docker-compose command: 'logs'" in out

    out = check_command("rapydo stop")
    assert "Stack stopped" in out

    out = check_command("rapydo restart")
    assert "Stack restarted" in out

    out = check_command("rapydo remove")
    assert "docker-compose command: 'stop'" in out
    assert "Stack removed" in out

    out = check_command("rapydo remove --networks")
    assert "Stack removed" in out

    out = check_command("rapydo remove --all")
    assert "Stack removed" in out

    out = check_command("rapydo shell backend --command hostname")
    assert "No container found for backend_1" in out

    out = check_command("rapydo interfaces sqlalchemy --port 123 --detach")
    assert "Launching interface: sqlalchemyui" in out
    assert "docker-compose command: 'run'" in out

    out = check_command("rapydo ancestors XYZ")
    assert "No parent found for XYZ" in out

    out = check_command("rapydo ssl")
    assert "No container found for proxy_1" in out
    out = check_command("rapydo ssl --volatile")
    assert "No container found for proxy_1" in out
    assert "Creating test_certificates-proxy_1" in out
    out = check_command("rapydo ssl --force")
    assert "No container found for proxy_1" in out
    out = check_command("rapydo ssl --chain-file /file")
    assert "Invalid chain file (you provided /file)" in out
    out = check_command("rapydo ssl --key-file /file")
    assert "Invalid chain file (you provided none)" in out
    f = "projects/test/project_configuration.yaml"
    out = check_command("rapydo ssl --chain-file {}".format(f))
    assert "Invalid key file (you provided none)" in out
    out = check_command("rapydo ssl --chain-file {} --key-file /file".format(f))
    assert "Invalid key file (you provided /file)" in out
    out = check_command("rapydo ssl --chain-file {f} --key-file {f}".format(f=f))
    assert "Unable to automatically perform the requested operation" in out
    assert "You can execute the following commands by your-self:" in out

    out = check_command("rapydo dhparam")
    assert "No container found for proxy_1" in out

    out = check_command("rapydo formatter")
    # assert "All done!" in out
    # This is because no endpoint is implemented in this project...
    # assert "No paths given" in out

    out = check_command(
        "rapydo formatter --submodule http-api/restapi --folder resources"
    )
    # assert "All done!" in out

    out = check_command("rapydo version")
    # assert __version__ in out

    out = check_command("rapydo volatile backend --command hostname")
    # assert "backend-server" in out

    out = check_command("rapydo install --editable auto")
    out = check_command("rapydo install --user auto")
    out = check_command("rapydo install auto")
