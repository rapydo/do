# -*- coding: utf-8 -*-

import sys

__version__ = '0.5.1'

FRAMEWORK_NAME = 'RAPyDo'
# PROJECT_YAML_SPECSDIR = 'specs'
COMPOSE_ENVIRONMENT_FILE = '.env'
SUBMODULES_DIR = 'submodules'
PLACEHOLDER = '#@$%-REPLACE-#@%$-ME-#@$%'

##################
# NOTE: telling the app if testing or not
# http://j.mp/2uifoza
TESTING = hasattr(sys, '_called_from_test')
