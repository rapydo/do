import os
# import shutil
from plumbum import local
from controller.arguments import ArgParser
from controller.app import Application


def exec_command(capfd, command):
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

    out, _ = capfd.readouterr()
    out = out.replace('\r', '').split("\n")

    for o in out:
        print(o)

    return out


def test_all(capfd):

    out = exec_command(capfd, "rapydo create test")
    assert "Missing authentication service, add --auth option" in out

    out = exec_command(capfd, "rapydo create test --auth xyz")
    assert "Invalid authentication service: xyz" in out

    out = exec_command(capfd, "rapydo create test --auth sql")
    assert "Missing frontend framework, add --frontend option" in out

    out = exec_command(capfd, "rapydo create test --auth sql --frontend xyz")
    assert "Invalid frontend framework: xyz" in out

    out = exec_command(capfd, "rapydo create test --auth sql --frontend angular")
    assert "Project test successfully created" in out

    out = exec_command(capfd, "rapydo create test --auth sql --frontend angular")
    assert "Current folder is not empty, cannot create a new project here." in out

    out = exec_command(capfd, "rapydo create test --auth sql --frontend angular --current --force")
    assert "Project test successfully created" in out

    # In this case the command should create/modify nothing... to be tested!
    out = exec_command(capfd, "rapydo create test --auth sql --frontend angular --current")
    assert "Project test successfully created" in out

    out = exec_command(capfd, "rapydo init")
    assert "Project initialized" in out

    out = exec_command(capfd, "rapydo pull")
    assert "Base images pulled from docker hub" in out

    # Skipping main because we are on a fake git repository
    out = exec_command(capfd, "rapydo update -i main")
    assert "All updated" in out

    # Selected a very fast service to speed up tests
    out = exec_command(capfd, "rapydo -s rabbit build --core")
    assert "Core images built" in out
    assert "No custom images to build" in out

    # Skipping main because we are on a fake git repository
    out = exec_command(capfd, "rapydo check -i main")
    assert "Checks completed" in out

    out = exec_command(capfd, "rapydo check -i main --check-permissions")
    assert "Checks completed" in out

    out = exec_command(capfd, "rapydo list --env")
    assert "List env variables:" in out

    out = exec_command(capfd, "rapydo list --args")
    assert "List of configured rapydo arguments:" in out

    out = exec_command(capfd, "rapydo list --active-services")
    assert "List of active services:" in out

    out = exec_command(capfd, "rapydo list --submodules")
    assert "List of submodules:" in out

    out = exec_command(capfd, "rapydo dump")
    assert "Config dump: docker-compose.yml" in out

    os.remove(".projectrc")

    command = local["cp"]
    command(["-r", "projects/test", "projects/second"])

    out = exec_command(capfd, "rapydo check -i main --no-git --no-builds")
    assert "Please add the --project option with one of the following:" in out

    out = exec_command(capfd, "rapydo -p test check -i main --no-git --no-builds")
    assert "Checks completed" in out

    out = exec_command(capfd, "rapydo -p invalid_character check -i main --no-git --no-builds")
    assert "Wrong project name, _ is not a valid character." in out

    out = exec_command(capfd, "rapydo -p celery check -i main --no-git --no-builds")
    assert "You selected a reserved name, invalid project name: celery" in out

    out = exec_command(capfd, "rapydo --project test init")
    assert "Project initialized" in out

    out = exec_command(capfd, "rapydo check -i main --no-git --no-builds")
    assert "Checks completed" in out

    out = exec_command(capfd, "rapydo start")
    assert "docker-compose command: 'up'" in out
    assert "Stack started" in out

    out = exec_command(capfd, "rapydo status")
    assert "docker-compose command: 'ps'" in out

    # Template project is based on sql
    exec_command(capfd, "rapydo verify neo4j")
    # This output is not capture, since it is produced by the backend
    # assert 'Service "neo4j" was NOT detected' in out

    exec_command(capfd, "rapydo verify postgres")
    # This output is not capture, since it is produced by the backend
    # assert "Service postgres is reachable" in out

    exec_command(capfd, "rapydo scale backend=1")

    exec_command(capfd, "rapydo logs")
    # FIXME: how is possible that this message is not found??
    # assert "docker-compose command: 'logs'" in out

    out = exec_command(capfd, "rapydo stop")
    assert "Stack stopped" in out

    out = exec_command(capfd, "rapydo restart")
    assert "Stack restarted" in out

    out = exec_command(capfd, "rapydo remove")
    assert "docker-compose command: 'stop'" in out
    assert "Stack removed" in out

    out = exec_command(capfd, "rapydo remove --networks")
    assert "Stack removed" in out

    out = exec_command(capfd, "rapydo remove --all")
    assert "Stack removed" in out

    exec_command(capfd, "rapydo interfaces sqlalchemy --port 123 --detach")
    exec_command(capfd, "rapydo ancestors XYZ")
    exec_command(capfd, "rapydo ssl")
    exec_command(capfd, "rapydo dhparam")

    out = exec_command(capfd, "rapydo formatter")
    assert "All done!" in out

    # out = exec_command(capfd, "rapydo volatile backend --command hostname")
    # assert "backend-server" in out

    # out = exec_command(capfd, "rapydo install --editable auto")
    # out = exec_command(capfd, "rapydo install --user auto")
    # out = exec_command(capfd, "rapydo install auto")
