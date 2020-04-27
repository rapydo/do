import os
import shutil
from git import Repo
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

    # selected this to enable rabbit and test the build command with a very build
    TEST_PROJECT = "celerytest"

    # INIT on rapydo-core
    out = exec_command(capfd, "rapydo --project {} init".format(TEST_PROJECT))
    assert "Project initialized" in out

    out = exec_command(capfd, "rapydo pull")
    assert "Base images pulled from docker hub" in out

    # UPDATE on rapydo-core
    out = exec_command(capfd, "rapydo update")
    assert "All updated" in out

    # Selected a very fast service to speed up tests
    out = exec_command(capfd, "rapydo -s rabbit build --rebuild-templates")
    assert "Images built" in out

    # CHECK on rapydo-core
    out = exec_command(capfd, "rapydo check")
    assert "Checks completed" in out

    # CHECK on rapydo-core by enabling permissions checks
    out = exec_command(capfd, "rapydo check --check-permissions")
    assert "Checks completed" in out

    # NOW we are on a fork of rapydo-core
    gitobj = Repo(".")
    gitobj.remotes.origin.set_url("just_a_non_url")

    out = exec_command(capfd, "rapydo init")
    assert "Project initialized" in out

    out = exec_command(capfd, "rapydo list --env")
    assert "List env variables:" in out

    out = exec_command(capfd, "rapydo list --args")
    assert "List of configured rapydo arguments:" in out

    out = exec_command(capfd, "rapydo list --services")
    assert "List of active services:" in out

    out = exec_command(capfd, "rapydo list --submodules")
    assert "List of submodules:" in out

    out = exec_command(capfd, "rapydo dump")
    assert "Config dump: docker-compose.yml" in out

    os.remove(".projectrc")

    command = local["cp"]
    command(["-r", "projects/{}".format(TEST_PROJECT), "projects/second"])

    out = exec_command(capfd, "rapydo check -s")
    assert "Please add the --project option with one of the following:" in out

    out = exec_command(capfd, "rapydo -p {} check -s".format(TEST_PROJECT))
    assert "Checks completed" in out

    out = exec_command(capfd, "rapydo -p invalid_character check -s")
    assert "Wrong project name, _ is not a valid character." in out

    out = exec_command(capfd, "rapydo -p celery check -s")
    assert "You selected a reserved name, invalid project name: celery" in out

    out = exec_command(capfd, "rapydo --project {} init".format(TEST_PROJECT))
    assert "Project initialized" in out

    out = exec_command(capfd, "rapydo check -s")
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

    # # exec_command(capfd, "rapydo create test")
    # # assert 'You are on a git repo, unable to continue' in out

    # current_folder = os.getcwd()
    # # DANGER!! Delete everything!!!
    # for f in os.listdir(current_folder):
    #     p = os.path.join(current_folder, f)
    #     if os.path.isfile(p):
    #         os.unlink(p)
    #     elif os.path.isdir(p):
    #         shutil.rmtree(p)

    # # testing a command from outside project dir
    # out = exec_command(capfd, "rapydo check --no-git --no-builds")
    # assert "Folder not found: projects" in out

    # out = exec_command(capfd, "rapydo create test")
    # assert "Project test successfully created" in out
    exec_command(capfd, "rapydo create test")
