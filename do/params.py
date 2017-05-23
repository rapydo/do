# -*- coding: utf-8 -*-

import argparse
from do.utils.logs import get_logger
log = get_logger(__name__)


##########################
# Arguments definition
parser = argparse.ArgumentParser(
    prog='do', description='Do things on this project'
)

parser.add_argument(
    '--project', type=str, metavar='PROJECT_NAME', default='vanilla',
    help='Your project name which forked RAPyDo core as vanilla customization')
parser.add_argument(
    '--execute_build', type=bool, metavar='TRUE_OR_FALSE', default=False,
    help='Force build of templates docker images')
parser.add_argument(
    '--blueprint', type=str, metavar='CONTAINERS_YAML_BLUEPRINT',
    required=True, help='Blueprint marker of the configuration to launch')

# Reading input parameters
args = parser.parse_args()
args = vars(args)
log.very_verbose("Parsed args: %s" % args)
