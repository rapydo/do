# -*- coding: utf-8 -*-

import os

FRAMEWORK_NAME = 'RAPyDo'

PROJECT_DIR = os.curdir

CONTAINERS_YAML_DIRNAME = 'containers'
PROJECT_YAML_SPECSDIR = 'specs'
PROJECT_CONF_FILENAME = 'project_configuration'

GIT_EXT = 'git'
GITHUB_PROTOCOL = 'https'
GITHUB_DOMAIN = 'github.com'
GITHUB_SITE = f"{GITHUB_PROTOCOL}://{GITHUB_DOMAIN}"
GITHUB_RAPYDO_COMPANY = 'rapydo'

COMMANDS = {
    'check':
        f"verify if currently compliant to {FRAMEWORK_NAME} specs",
    'init':
        f"make compliant to latest {FRAMEWORK_NAME} (if not yet) ",
    'launch':
        f"start your framework with current blueprint",
    # '':
    #     f"",
    'clean':
        f"remove all containers, networks (and volumes)",
}

containers_yaml_path = os.path.join(os.curdir, CONTAINERS_YAML_DIRNAME)
project_specs_yaml_path = os.path.join(os.curdir, PROJECT_YAML_SPECSDIR)

# FIXME: get this from rapydo.utils
defaults_path = os.path.join('backend', 'rapydo', 'confs')
