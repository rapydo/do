# -*- coding: utf-8 -*-

import os

__version__ = '0.3.dev1'

FRAMEWORK_NAME = 'RAPyDo'

PROJECT_DIR = os.curdir

CONTAINERS_YAML_DIRNAME = 'containers'
PROJECT_YAML_SPECSDIR = 'specs'
PROJECT_CONF_FILENAME = 'project_configuration'

# FIXME: what is the best practice of getting this path?
ABSOLUTE_PATH = os.path.dirname(os.path.realpath(__file__))  # + "/.."

containers_yaml_path = os.path.join(os.curdir, CONTAINERS_YAML_DIRNAME)
project_specs_yaml_path = os.path.join(os.curdir, PROJECT_YAML_SPECSDIR)


# TODO: move below in checks module (rapydo.utils package?)

BASE_OPTION = '--version'


def check_executable(executable, option=BASE_OPTION, log=None):

    from subprocess import check_output
    try:
        stdout = check_output([executable, option])
        output = stdout.decode()
    except OSError:
        return None
    else:
        if option == BASE_OPTION:
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
