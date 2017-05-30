# -*- coding: utf-8 -*-

import os
import sys
import argparse
from do.utils.myyaml import load_yaml_file
from do import ABSOLUTE_PATH


def prepare_params(options):
    option_type = str
    if options.get('type') == 'bool':
        option_type = bool
    default = options.get('default')
    myhelp = "%s [default: %s]" % (options.get('help'), default)

    return {
        'type': option_type,
        'default': default,
        'metavar': options.get('metavalue'),
        'help': myhelp
    }


parse_conf = load_yaml_file('argparser', path=ABSOLUTE_PATH, logger=False)

# Arguments definition
parser = argparse.ArgumentParser(
    prog=sys.argv[0],
    description=parse_conf.get('description')
)

# PARAMETERS
for option_name, options in sorted(parse_conf.get('options', {}).items()):
    params = prepare_params(options)
    parser.add_argument('--%s' % option_name, **params)

# Sub-parser of commands [check, init, etc]
main_command = parse_conf.get('action')

subparsers = parser.add_subparsers(
    title='Sub commands',
    dest=main_command.get('name'),
    help=main_command.get('help')
)

subparsers.required = True

for command_name, options in sorted(parse_conf.get('subcommands', {}).items()):

    # Creating a parser for each sub-command [check, init, etc]
    subparse = subparsers.add_parser(
        command_name, help=options.get('description'))

    controlcommands = options.get('controlcommands', {})
    # Some subcommands can have further subcommands [control start, stop, etc]
    if len(controlcommands) > 0:
        innerparser = subparse.add_subparsers(
            dest='controlcommand'
        )
        innerparser.required = options.get('controlrequired', False)
        for subcommand, suboptions in controlcommands.items():
            subcommand_help = suboptions.pop(0)
            # Creating a parser for each sub-sub-command [control start, stop]
            innerparser.add_parser(subcommand, help=subcommand_help)

    for option_name, suboptions in options.get('suboptions', {}).items():
        params = prepare_params(suboptions)
        subparse.add_argument('--%s' % option_name, **params)

# Reading input parameters
current_args = parser.parse_args()
current_args = vars(current_args)

# Log level
os.environ['DEBUG_LEVEL'] = current_args.get('log_level')

if True:
    from do.utils.logs import get_logger
    log = get_logger(__name__)
    log.verbose("Parsed arguments: %s" % current_args)
