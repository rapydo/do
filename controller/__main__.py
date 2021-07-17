"""
    Command line script: main function
"""

from python_on_whales.utils import DockerException

from controller import log
from controller.app import Application


def main() -> None:
    try:
        Application.load_projectrc()
        controller = Application()
        controller.app()
    except DockerException as e:
        log.critical("Uncatched exception: {}", type(e))
        print("")
        log.critical(e)


if __name__ == "__main__":
    main()
