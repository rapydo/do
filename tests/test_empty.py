
from controller.arguments import ArgParser
from controller.app import Application
from utilities.logs import get_logger
log = get_logger(__name__)


def test_do():
    arguments = ArgParser(
        args=['/usr/local/bin/rapydo', 'check']
    )
    Application(arguments)

    assert True
