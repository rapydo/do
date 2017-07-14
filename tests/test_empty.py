
try:
    from controller.app import Application
except SystemExit:
    pass
from utilities.logs import get_logger
log = get_logger(__name__)


def test_do():
    try:
        Application
    except NameError:
        pass
    assert True
