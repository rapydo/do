# -*- coding: utf-8 -*-

"""
Pythonic checks on the current system
"""

# from rapydo.utils.logs import get_logger

# log = get_logger(__name__)


DEFAULT_BIN_OPTION = '--version'


def check_executable(executable, option=DEFAULT_BIN_OPTION, log=None):

    from subprocess import check_output
    try:
        stdout = check_output([executable, option])
        output = stdout.decode()
    except OSError:
        return None
    else:
        if option == DEFAULT_BIN_OPTION:
            try:
                # try splitting on coma and/or parenthesis
                # then last element on spaces
                output = output \
                    .split('(')[0].split(',')[0] \
                    .split()[::-1][0]
            except BaseException:
                pass
        return output


def check_package(package_name):

    from importlib import import_module
    try:
        package = import_module(package_name)
    except ModuleNotFoundError:
        return None
    else:
        return package.__version__


def check_internet(test_site='https://www.google.com'):

    import requests
    try:
        requests.get(test_site)
    except requests.ConnectionError:
        return False
    else:
        return True
