
from controller.arguments import ArgParser
from controller.app import Application
from utilities.logs import get_logger
log = get_logger(__name__)


def test_do():
    arguments = ArgParser(
        args=['/usr/local/bin/rapydo', 'init']
    )
    try:
        Application(arguments)
    # NOTE: docker-compose calls SystemExit at the end of the command...
    except SystemExit:
        log.info('completed')

    arguments = ArgParser(
        args=['/usr/local/bin/rapydo', 'update']
    )
    try:
        Application(arguments)
    # NOTE: docker-compose calls SystemExit at the end of the command...
    except SystemExit:
        log.info('completed')

    arguments = ArgParser(
        args=['/usr/local/bin/rapydo', 'start']
    )

    try:
        Application(arguments)
    # NOTE: docker-compose calls SystemExit at the end of the command...
    except SystemExit:
        log.info('completed')

    arguments = ArgParser(
        args=['/usr/local/bin/rapydo', 'remove']
    )

    try:
        Application(arguments)
    # NOTE: docker-compose calls SystemExit at the end of the command...
    except SystemExit:
        log.info('completed')
    assert True
