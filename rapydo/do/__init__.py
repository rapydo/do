# -*- coding: utf-8 -*-

import os

__version__ = '0.1.rc1'

FRAMEWORK_NAME = 'RAPyDo'

CONTAINERS_YAML_DIRNAME = 'containers'
PROJECT_YAML_SPECSDIR = 'specs'
PROJECT_CONF_FILENAME = 'project_configuration'
COMPOSE_ENVIRONMENT_FILE = '.env'
PLACEHOLDER = '#@$%-REPLACE-#@%$-ME-#@$%'

# FIXME: move me where it's used
containers_yaml_path = os.path.join(os.curdir, CONTAINERS_YAML_DIRNAME)
project_specs_yaml_path = os.path.join(os.curdir, PROJECT_YAML_SPECSDIR)
