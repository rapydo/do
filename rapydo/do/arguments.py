# -*- coding: utf-8 -*-

"""
Automatically create and parse commands
based on a YAML configuration file.

NOTE: we can't have a logger here,
before knowing the level of debug.
"""

import os
import sys
import argparse
from rapydo.do import __version__
from rapydo.utils import helpers
from rapydo.utils.myyaml import load_yaml_file


def prepare_params(options):

    pconf = {}
    default = options.get('default')
    pconf['default'] = default

    myhelp = "%s [default: %s]" % (options.get('help'), default)
    pconf['help'] = myhelp

    if options.get('type') == 'bool':

        if default:
            pconf['action'] = 'store_false'
        else:
            pconf['action'] = 'store_true'

    else:
        # type and metavar are allowed for bool
        pconf['type'] = str
        pconf['metavar'] = options.get('metavalue')

    if 'alias' in options:
        pconf['alias'] = options['alias']

    if 'positional' in options:
        pconf['positional'] = options['positional']

    return pconf


# ##########################
# Check on format
for element in sys.argv:
    if '_' in element:
        raise ValueError(
            "Wrong \"%s\" option provided.\n" % element +
            "Arguments containing '_' are not allowed.\n" +
            "Use '-' instead\n")
# NOTE: the standard is to use only '-' separators for arguments
# but beware that argparse converts them into '_' when you want to retrieve it


# ##########################
# READ MAIN FILE WITH COMMANDS AND OPTIONS
parse_conf = load_yaml_file(
    'argparser', path=helpers.script_abspath(__file__),
    logger=False
)

# ##########################
# READ PROJECT INIT FILE: .projectrc
pinit_conf = load_yaml_file(
    '.projectrc',
    path=helpers.current_dir(),
    skip_error=True, logger=False, extension=None
)

# Mix with parse_conf
for key, value in pinit_conf.items():
    value = pinit_conf.get(key, None)

    if value is None:
        continue

    if not isinstance(value, dict):
        # This is a first level option
        if key in parse_conf['options']:
            parse_conf['options'][key]['default'] = value
        else:
            print("\nUnknown parameter %s found in .projectrc\n" % key)
    else:
        # This is a second level parameter
        if key not in parse_conf['subcommands']:
            print("\nUnknown command %s found in .projectrc\n" % key)
        else:
            conf = parse_conf['subcommands'][key]['suboptions']
            for subkey, subvalue in value.items():
                if subkey in conf:
                    conf[subkey]['default'] = subvalue
                else:
                    print(
                        "\nUnknown parameter %s/%s found in .projectrc\n"
                        % (key, subkey)
                    )


# ##########################
# Arguments definition
parser = argparse.ArgumentParser(
    prog=sys.argv[0],
    description=parse_conf.get('description')
)

# PARAMETERS
for option_name, options in sorted(parse_conf.get('options', {}).items()):
    params = prepare_params(options)
    alias = params.pop('alias', None)
    param_name = '--%s' % option_name
    if alias is None:
        parser.add_argument(param_name, **params)
    else:
        parser.add_argument(param_name, '-%s' % alias, **params)

parser.add_argument('--version', action='version',
                    version='rapydo version %s' % __version__)
# Sub-parser of commands [check, init, etc]
main_command = parse_conf.get('action')

subparsers = parser.add_subparsers(
    title='Available commands',
    dest=main_command.get('name'),
    help=main_command.get('help')
)

subparsers.required = True

# ##########################
# COMMANDS

# BASE normal commands
mycommands = parse_conf.get('subcommands', {})

for command_name, options in sorted(mycommands.items()):

    # Creating a parser for each sub-command [check, init, etc]
    subparse = subparsers.add_parser(
        command_name, help=options.get('description'))

    # controlcommands = options.get('controlcommands', {})
    # # Some subcommands can have further subcommands
    # [control start, stop, etc]
    # if len(controlcommands) > 0:
    #     innerparser = subparse.add_subparsers(
    #         dest='controlcommand'
    #     )
    #     innerparser.required = options.get('controlrequired', False)
    #     for subcommand, suboptions in controlcommands.items():
    #         subcommand_help = suboptions.pop(0)
    #         # Creating a parser for each sub-sub-command [control start/stop]
    #         innerparser.add_parser(subcommand, help=subcommand_help)

    for option_name, suboptions in options.get('suboptions', {}).items():
        params = prepare_params(suboptions)
        alias = params.pop('alias', None)
        positional = params.pop('positional', False)
        param_name = '--%s' % option_name
        if positional:
            subparse.add_argument(option_name, **params)
        elif alias is None:
            subparse.add_argument(param_name, **params)
        else:
            subparse.add_argument(param_name, '-%s' % alias, **params)

# ##########################
# Print usage if no arguments provided
if len(sys.argv) == 1:
    parser.print_help()
    sys.exit(1)

# ##########################
# Reading input parameters

"""
# Partial parsing
# https://docs.python.org/3.4/library/argparse.html#partial-parsing
# Example
# https://gist.github.com/von/949337/
"""

# current_args = parser.parse_args()
current_args_namespace, remaining_args = parser.parse_known_args()
current_args = vars(current_args_namespace)

# custom commands as a separate parser
extra_parser = argparse.ArgumentParser(
    description='Custom rapydo commands from your project configuration',
    add_help=False, usage='\n$ rapydo custom CUSTOM_COMMAND'
)
extra_command_parser = extra_parser.add_subparsers(
    title='Available custom commands',
    dest='custom', help='list of custom commands'
)
extra_command_parser.required = True

# ##########################
# Log level
key = 'DEBUG_LEVEL'
os.environ[key] = current_args.get('log_level')

if os.environ.get(key) is not None:
    from rapydo.utils.logs import get_logger
    log = get_logger(__name__)
    log.verbose("Parsed arguments: %s" % current_args)
