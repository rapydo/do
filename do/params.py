# -*- coding: utf-8 -*-

import os
import sys
import argparse
from do import COMMANDS, FRAMEWORK_NAME

##########################
# Arguments definition
parser = argparse.ArgumentParser(
    prog=sys.argv[0],
    description='Do actions with your {FRAMEWORK_NAME} project'
)

# parser.add_argument(
#     '--project', type=str, metavar='PROJECT_NAME', default='vanilla',
#     help='Project which forked RAPyDo')

# PARAMETERS

parser.add_argument(
    '--log-level', type=str,
    metavar='LEVEL_OF_DEBUGGER', default='DEBUG',
    help='Level of verbosity [default: DEBUG]')

parser.add_argument(
    '--blueprint', type=str,
    metavar='CONTAINERS_YAML_BLUEPRINT', default='debug',
    help='Blueprint marker of the configuration to launch [default: debug]')

parser.add_argument(
    '--execute_build', type=bool, metavar='TRUE_OR_FALSE', default=False,
    help='Force build of templates docker images [default: False]')

# COMMANDS
myhelp = ""
for name, description in COMMANDS.items():
    myhelp += f"{name}:\t\"{description}\"\n"
parser.add_argument('command', help=myhelp)

# Reading input parameters
args = parser.parse_args()
args = vars(args)

# Log level
os.environ['DEBUG_LEVEL'] = args.get('log_level')

if True:
    from do.utils.logs import get_logger
    log = get_logger(__name__)
    log.verbose("Parsed args: %s" % args)
