import sys

from python_on_whales.utils import DockerException

from controller import log
from controller.app import Application


def main() -> None:
    try:
        Application.load_projectrc()
        controller = Application()
        controller.app()
    except DockerException as e:  # pragma: no cover
        log.critical("Uncatched exception: {}", type(e))
        sys.exit(str(e))


if __name__ == "__main__":
    main()
