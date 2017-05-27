# -*- coding: utf-8 -*-

import os
import requests

FRAMEWORK_NAME = 'RAPyDo'

PROJECT_DIR = os.curdir

CONTAINERS_YAML_DIRNAME = 'containers'
PROJECT_YAML_SPECSDIR = 'specs'
PROJECT_CONF_FILENAME = 'project_configuration'

# FIXME: @packaging ?
ABSOLUTE_PATH = os.path.dirname(os.path.realpath(__file__)) + "/.."

containers_yaml_path = os.path.join(os.curdir, CONTAINERS_YAML_DIRNAME)
project_specs_yaml_path = os.path.join(os.curdir, PROJECT_YAML_SPECSDIR)


def check_internet(test_site='https://www.google.com'):
    try:
        requests.get(test_site)
    except requests.ConnectionError:
        return False
    else:
        return True
