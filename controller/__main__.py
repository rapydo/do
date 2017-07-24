# -*- coding: utf-8 -*-

"""
    Command line script: main function
"""

import better_exceptions as be
from controller.arguments import ArgParser


def activate_log():
    from utilities.logs import get_logger
    return get_logger(__name__)


def activate_better_exceptions():
    be

    # Ok, I'm just trying to remove the annoying message from Landscape.io:
    # Statement seems to have no effect
    if be is None:
        print("Errors while activating better exceptions?")


def main():
    activate_better_exceptions()
    try:
        arguments = ArgParser()

        from controller.app import Application
        Application(arguments)
    except KeyboardInterrupt:
        log = activate_log()
        log.critical("Interrupted by the user")
    else:
        log = activate_log()
        log.verbose("Application completed")


if __name__ == '__main__':
    main()
