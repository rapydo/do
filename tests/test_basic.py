

from io import StringIO
import logging
from controller.arguments import ArgParser
from controller.app import Application
from utilities.logs import get_logger
log = get_logger(__name__)


def capture_loggers():
    log_capture_string = StringIO()
    from controller.app import log
    capture_logger(log, log_capture_string)

    return log_capture_string


def capture_logger(log, output_string):
    ch = logging.StreamHandler(output_string)
    # ch.setLevel(logging.DEBUG)
    log.addHandler(ch)


def exec_command(command):
    log_capture_string = capture_loggers()
    command = command.split(" ")
    arguments = ArgParser(args=command)

    try:
        Application(arguments)
    # NOTE: docker-compose calls SystemExit at the end of the command...
    except SystemExit:
        log.info('completed')

    log_contents = log_capture_string.getvalue().split("\n")
    log_capture_string.close()

    return log_contents


def test_do():

    log_contents = exec_command("rapydo init")
    assert "Project initialized" in log_contents

    exec_command("rapydo update")
    exec_command("rapydo start")
    exec_command("rapydo remove")

    assert True
