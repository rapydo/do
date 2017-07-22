
# import logging
from controller.arguments import ArgParser
from controller.app import Application
from utilities.logs import get_logger

log = get_logger(__name__)


def cut_log(message):
    try:
        i = message.index("]")
        return message[i + 2:]
    except ValueError:
        print(message)
        return message


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

    out = [cut_log(x) for x in out]
    err = [cut_log(x) for x in err]

    for e in err:
        print(e)

    return out, err


def test_do(capfd):

    # import logging
    # formatter = logging.Formatter('%(levelname)s - %(message)s')
    # loggers = logging.Logger.manager.loggerDict.items()
    # print(loggers)
    # for _, logger in loggers:
    #     if not isinstance(logger, logging.Logger):
    #         continue
    #     for h in logger.handlers:
    #         h.setFormatter(formatter)

    _, err = exec_command(capfd, "rapydo init")
    assert "Project initialized" in err

    _, err = exec_command(capfd, "rapydo update")
    assert "All updated" in err

    # _, err = exec_command(capfd, "rapydo build")
    # assert "Image built" in err

    _, err = exec_command(capfd, "rapydo check")
    assert "All checked" in err

    out, err = exec_command(capfd, "rapydo env")
    assert "project: template" in out

    _, err = exec_command(capfd, "rapydo start")
    assert "Stack started" in err

    # Output not checked
    exec_command(capfd, "rapydo status")
    exec_command(capfd, "rapydo log")
    exec_command(capfd, "rapydo bower-install test")
    exec_command(capfd, "rapydo update test")

    _, err = exec_command(capfd, "rapydo toggle-freeze")
    assert "Stack paused" in err

    _, err = exec_command(capfd, "rapydo toggle-freeze")
    assert "Stack unpaused" in err

    _, err = exec_command(capfd, "rapydo stop")
    assert "Stack stoped" in err

    _, err = exec_command(capfd, "rapydo restart")
    assert "Stack restarted" in err

    _, err = exec_command(capfd, "rapydo remove")
    assert "Stack removed" in err

    _, err = exec_command(capfd, "rapydo clean")
    assert "Stack cleaned" in err
