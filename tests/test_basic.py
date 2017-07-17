
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

    # formatter = logging.Formatter('%(levelname)s - %(message)s')
    # loggers = logging.Logger.manager.loggerDict.items()
    # for _, logger in loggers:
    #     if not isinstance(logger, logging.Logger):
    #         continue
    #     for h in logger.handlers:
    #         h.setFormatter(formatter)

    arguments = ArgParser(args=command)

    try:
        Application(arguments)
        pass
    # NOTE: docker-compose calls SystemExit at the end of the command...
    except SystemExit:
        log.info('completed')

    out, err = capfd.readouterr()
    err = err.split("\n")

    err = [cut_log(x) for x in err]

    for e in err:
        print(e)

    return err


def test_do(capfd):

    err = exec_command(capfd, "rapydo init")

    assert "Project initialized" in err

    exec_command(capfd, "rapydo update")
    exec_command(capfd, "rapydo start")
    exec_command(capfd, "rapydo remove")

    assert True
