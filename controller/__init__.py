# -*- coding: utf-8 -*-

import sys

# NOTE: telling the app if testing or not
# http://j.mp/2uifoza

TESTING = hasattr(sys, '_called_from_test')

FRAMEWORK_NAME = 'RAPyDo'
__version__ = '0.5.0'

# PROJECT_YAML_SPECSDIR = 'specs'
COMPOSE_ENVIRONMENT_FILE = '.env'
SUBMODULES_DIR = 'submodules'
PLACEHOLDER = '#@$%-REPLACE-#@%$-ME-#@$%'
