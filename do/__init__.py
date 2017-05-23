# -*- coding: utf-8 -*-

import os

CONTAINERS_YAML_DIRNAME = 'containers'
PROJECT_YAML_SPECSDIR = 'specs'
PROJECT_CONF_FILENAME = 'project_configuration'

containers_yaml_path = os.path.join(os.curdir, CONTAINERS_YAML_DIRNAME)
project_specs_yaml_path = os.path.join(os.curdir, PROJECT_YAML_SPECSDIR)

# FIXME: get this from rapydo.utils
defaults_path = os.path.join('backend', 'rapydo', 'confs')
