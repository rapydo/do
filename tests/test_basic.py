
# import logging
from controller.arguments import ArgParser
from controller.app import Application
from utilities.logs import get_logger

log = get_logger(__name__)


def exec_command(capfd, command):
    command = command.split(" ")

    arguments = ArgParser(args=command)

    try:
        Application(arguments)
    # NOTE: docker-compose calls SystemExit at the end of the command...
    except SystemExit:
        log.info('completed')

    out, err = capfd.readouterr()
    out = out.split("\n")
    err = err.split("\n")

    for e in err:
        print(e)

    return out, err


def test_do(capfd):

    _, err = exec_command(capfd, "rapydo init")
    assert "INFO Project initialized" in err

    _, err = exec_command(capfd, "rapydo update")
    assert "INFO All updated" in err

    # _, err = exec_command(capfd, "rapydo build")
    # assert "Image built" in err

    _, err = exec_command(capfd, "rapydo check")
    assert "INFO All checked" in err

    out, err = exec_command(capfd, "rapydo env")
    assert "project: template" in out

    _, err = exec_command(capfd, "rapydo start")
    assert "INFO Stack started" in err

    # Output not checked
    exec_command(capfd, "rapydo status")
    exec_command(capfd, "rapydo log")
    exec_command(capfd, "rapydo bower-install test")
    exec_command(capfd, "rapydo update test")

    _, err = exec_command(capfd, "rapydo toggle-freeze")
    assert "INFO Stack paused" in err

    _, err = exec_command(capfd, "rapydo toggle-freeze")
    assert "INFO Stack unpaused" in err

    _, err = exec_command(capfd, "rapydo stop")
    assert "INFO Stack stoped" in err

    _, err = exec_command(capfd, "rapydo restart")
    assert "INFO Stack restarted" in err

    _, err = exec_command(capfd, "rapydo remove")
    assert "INFO Stack removed" in err

    _, err = exec_command(capfd, "rapydo clean")
    assert "INFO Stack cleaned" in err
