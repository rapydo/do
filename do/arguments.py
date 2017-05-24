# -*- coding: utf-8 -*-

import os
import sys
import argparse
from do.utils.myyaml import load_yaml_file

# FIXME: @packaging - how to specify a configuration file where the lib is?
ABSOLUTE_PATH = '/Users/projects/tmp/do'

parse_conf = load_yaml_file('argparser', path=ABSOLUTE_PATH, logger=False)

# Arguments definition
parser = argparse.ArgumentParser(
    prog=sys.argv[0],
    description=parse_conf.get('description')
)

# PARAMETERS
for option_name, option in parse_conf.get('options', {}).items():
    option_type = str
    if option.get('type') == 'bool':
        option_type = bool
    default = option.get('default')
    myhelp = f"{option.get('help')} [default: {default}]"
    parser.add_argument(
        f'--{option_name}', type=option_type,
        metavar=option.get('metavalue'), default=default, help=myhelp
    )

# COMMANDS
main_command = parse_conf.get('command')
subparsers = parser.add_subparsers(
    dest=main_command.get('name'),
    help=main_command.get('help')
)
subparsers.required = True

for command_name, options in parse_conf.get('subcommands', {}).items():
    subparse = subparsers.add_parser(
        command_name, help=options.get('description'))

    innercommands = options.get('innercommands', {})
    if len(innercommands) > 0:
        innerparser = subparse.add_subparsers(
            dest='innercommand'
        )
        innerparser.required = options.get('innerrequired', False)
        for subcommand, suboptions in innercommands.items():
            innerparser.add_parser(subcommand, help='some help')

# Reading input parameters
current_args = parser.parse_args()
current_args = vars(current_args)

# Log level
os.environ['DEBUG_LEVEL'] = current_args.get('log_level')

if True:
    from do.utils.logs import get_logger
    log = get_logger(__name__)
    log.verbose("Parsed arguments: %s" % current_args)
