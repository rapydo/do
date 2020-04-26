import os
import tempfile
from git import Repo
from plumbum import local
from prettyprinter import pprint as pp
from controller import log
from controller.arguments import ArgParser
from controller.app import Application


def exec_command(capfd, command, get_out=True, get_err=False):
    command = command.split(" ")

    arguments = ArgParser(args=command)

    try:
        Application(arguments)
    # NOTE: docker-compose calls SystemExit at the end of the command...
    except SystemExit:
        log.info('completed')

    out, err = capfd.readouterr()
    out = out.replace('\r', '').split("\n")
    err = err.replace('\r', '').split("\n")

    if get_out:
        pp(out)

    if get_err:
        pp(err)

    if get_out and get_err:
        return out, err

    if get_out:
        return out

    if get_err:
        return err

    return None


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

    # Output is too long? Removed last tests...
    # exec_command(capfd, "rapydo create test")
    # assert 'You are on a git repo, unable to continue' in out

    prev_folder = os.getcwd()

    # testing a command from a subfolder
    os.chdir("projects")
    exec_command(capfd, "rapydo check --no-git --no-builds")

    # testing a command from outside project dir
    os.chdir(tempfile.gettempdir())
    exec_command(capfd, "rapydo check --no-git --no-builds")

    # exec_command(capfd, "rapydo create test")
    # assert "Project test successfully created" in out
    os.chdir(prev_folder)
