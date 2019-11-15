# -*- coding: utf-8 -*-

import sys
from loguru import logger as log

log.remove()
log.add("rapydo-controller.log", level="WARNING", rotation="1 week", retention="4 weeks")
log.add(sys.stdout, colorize=True, format="<fg #FFF>{time:YYYY-MM-DD HH:mm:ss,SSS}</fg #FFF> [<level>{level}</level> <fg #666>{name}:{line}</fg #666>] <fg #FFF>{message}</fg #FFF>")
new_level = log.level("VERBOSE", no=1, color="<fg #666>")
log.level("INFO", color="<green>")


def verbose(*args, **kwargs):
    log.log("VERBOSE", *args, **kwargs)


def exit(*args, **kwargs):
    log.critical(*args, **kwargs)
    sys.exit(1)


log.verbose = verbose
log.exit = exit

__version__ = '0.7.0'

# FRAMEWORK_NAME = 'RAPyDo'
# PROJECT_YAML_SPECSDIR = 'specs'
COMPOSE_ENVIRONMENT_FILE = '.env'
SUBMODULES_DIR = 'submodules'
PROJECT_DIR = 'projects'
SWAGGER_DIR = 'swagger'
RAPYDO_CONFS = 'rapydo-confs'
RAPYDO_TEMPLATE = 'tests'
RAPYDO_GITHUB = "https://github.com/rapydo"
PLACEHOLDER = '**PLACEHOLDER**'
TEMPLATE_DIR = 'templates'
PROJECTRC = '.projectrc'
PROJECTRC_ALTERNATIVE = '.project.yml'
# Also configured in http-api
EXTENDED_PROJECT_DISABLED = "no_extended_project"
CONTAINERS_YAML_DIRNAME = 'confs'
BACKEND_DIR = 'backend'  # directory outside docker
BACKEND_PACKAGE = 'restapi'  # package inside rapydo-http
ENDPOINTS_CODE_DIR = 'apis'

# NOTE: telling the app if testing or not
# http://j.mp/2uifoza
TESTING = hasattr(sys, '_called_from_test')
