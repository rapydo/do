import os
from git import Repo
from prettyprinter import pprint as pp
from controller import log
from controller.arguments import ArgParser
from controller.compose import compose_log
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

    # create .projectrc
    with open('.projectrc', 'w') as f:
        f.write("project: sql")

    # INIT on rapydo-core
    out = exec_command(capfd, "rapydo init")
    assert "Project initialized" in out

    out = exec_command(capfd, "rapydo pull")
    assert "Base images pulled from docker hub" in out

    out = exec_command(capfd, "rapydo init")
    assert "Project initialized" in out

    # UPDATE on rapydo-core
    out = exec_command(capfd, "rapydo update")
    assert "All updated" in out

    out = exec_command(capfd, "rapydo build --rebuild-templates")
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

    from plumbum import local
    command = local["cp"]
    command(["-r", "projects/sql", "projects/second"])

    out = exec_command(capfd, "rapydo check -s")
    assert "Please select the --project option on one of the following:" in out

    out = exec_command(capfd, "rapydo -p sql check -s")
    assert "Checks completed" in out

    out = exec_command(capfd, "rapydo -p invalid_character check -s")
    assert "Wrong project name, _ is not a valid character." in out

    out = exec_command(capfd, "rapydo -p celery check -s")
    assert "You selected a reserved name, invalid project name: celery" in out

    # out = exec_command(capfd, "rapydo -p xyz check -s")
    # assert "Wrong project 'xyz'." in out
    # assert "Select one of the following:" in out

    # create .projectrc
    with open('.projectrc', 'w') as f:
        f.write("project: sql")

    out = exec_command(capfd, "rapydo check -s")
    assert "Checks completed" in out

    out = exec_command(capfd, "rapydo start")
    assert compose_log + "'up'" in out
    assert "Stack started" in out

    out = exec_command(capfd, "rapydo status")
    assert compose_log + "'ps'" in out

    # Template project is based on neo4j
    exec_command(capfd, "rapydo verify neo4j")
    # This output is not capture, since it is produced by the backend
    # assert 'Service "neo4j" was NOT detected' in out

    exec_command(capfd, "rapydo verify postgres")
    # This output is not capture, since it is produced by the backend
    # assert "Service postgres is reachable" in out

    exec_command(capfd, "rapydo scale backend=1")

    exec_command(capfd, "rapydo logs")
    # FIXME: how is possible that this message is not found??
    # assert compose_log + "'logs'" in out

    out = exec_command(capfd, "rapydo toggle-freeze")
    assert "Stack paused" in out

    out = exec_command(capfd, "rapydo toggle-freeze")
    assert "Stack unpaused" in out

    out = exec_command(capfd, "rapydo stop")
    assert "Stack stopped" in out

    out = exec_command(capfd, "rapydo restart")
    assert "Stack restarted" in out

    out = exec_command(capfd, "rapydo remove")
    assert compose_log + "'stop'" in out
    assert "Stack removed" in out

    out = exec_command(capfd, "rapydo remove --networks")
    assert "Stack removed" in out

    out = exec_command(capfd, "rapydo remove --all")
    assert "Stack removed" in out

    exec_command(capfd, "rapydo interfaces sqlalchemy --port 123 --detach")
    exec_command(capfd, "rapydo ancestors XYZ")
    exec_command(capfd, "rapydo ancestors ssl")
    exec_command(capfd, "rapydo ancestors ssl-dhparam")

    # Output is too long? Removed last tests...
    # exec_command(capfd, "rapydo create test")
    # assert 'You are on a git repo, unable to continue' in out

    prev_folder = os.getcwd()
    # testing a command from outside project dir
    os.chdir("/tmp")
    exec_command(capfd, "rapydo check --no-git --no-builds")
    # exec_command(capfd, "rapydo create test")
    # assert "Project test successfully created" in out
    os.chdir(prev_folder)
