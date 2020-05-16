# -*- coding: utf-8 -*-

import os
import sys
from loguru import logger as log

__version__ = '0.7.4'


# NOTE: telling the app if testing or not
# http://j.mp/2uifoza
TESTING = hasattr(sys, '_called_from_test') or os.environ.get('TESTING', '0') == '1'

LOGS_FOLDER = os.path.join("data", "logs")

LOGS_FILE = None
if os.path.isdir(LOGS_FOLDER):
    LOGS_FILE = os.path.join(LOGS_FOLDER, "rapydo-controller.log")

log.level("VERBOSE", no=1, color="<fg #666>")
log.level("INFO", color="<green>")


def verbose(*args, **kwargs):
    log.log("VERBOSE", *args, **kwargs)


def exit_msg(message="", *args, **kwargs):
    error_code = kwargs.pop('error_code', 1)
    if not isinstance(error_code, int):
        raise ValueError("Error code must be an integer")
    if error_code < 1:
        raise ValueError("Cannot exit with value below 1")
    if message:
        log.critical(message, *args, **kwargs)
    sys.exit(error_code)


log.verbose = verbose
log.exit = exit_msg

log.remove()

if TESTING:
    log.add(sys.stdout, colorize=False, format="{message}")
else:
    log.add(sys.stderr, colorize=True, format="<fg #FFF>{time:YYYY-MM-DD HH:mm:ss,SSS}</fg #FFF> [<level>{level}</level> <fg #666>{name}:{line}</fg #666>] <fg #FFF>{message}</fg #FFF>")

if LOGS_FILE is not None:
    try:
        log.add(LOGS_FILE, level="WARNING", rotation="1 week", retention="4 weeks")
    except PermissionError as e:
        log.error(e)
        LOGS_FILE = None

COMPOSE_ENVIRONMENT_FILE = '.env'
SUBMODULES_DIR = 'submodules'
PROJECT_DIR = 'projects'
TEMPLATE_DIR = 'templates'
# CONFS_DIR = os.path.join(SUBMODULES_DIR, 'do', 'controller', 'confs')
CONFS_DIR = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'confs')
PLACEHOLDER = '**PLACEHOLDER**'
PROJECTRC = '.projectrc'
PROJECTRC_ALTERNATIVE = '.project.yml'
EXTENDED_PROJECT_DISABLED = "no_extended_project"
CONTAINERS_YAML_DIRNAME = 'confs'
