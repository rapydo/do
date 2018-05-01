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
from controller import __version__
from utilities import helpers
from utilities.myyaml import load_yaml_file


class ArgParser(object):

    def __init__(self, args=None):
        if args is None:
            args = sys.argv

        self.current_args = {}
        self.host_configuration = {}
        # This method can raise ValueErrors
        self.check_args(args)

        # This method saves configuration objects in self
        self.read_configuration()

        # Arguments definition
        parser = argparse.ArgumentParser(
            prog=args[0],
            description=self.parse_conf.get('description')
        )

        # PARAMETERS
        sorted_options = sorted(self.parse_conf.get('options', {}).items())
        for option_name, options in sorted_options:
            self.add_parser_argument(parser, option_name, options)

        version_string = 'rapydo version %s' % __version__
        parser.add_argument('--version', action='version',
                            version=version_string)
        # Sub-parser of commands [check, init, etc]
        main_command = self.parse_conf.get('action')

        subparsers = parser.add_subparsers(
            title='Available commands',
            dest=main_command.get('name'),
            help=main_command.get('help')
        )

        subparsers.required = True

        # ##########################
        # COMMANDS

        # BASE normal commands
        mycommands = self.parse_conf.get('subcommands', {})

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
            #         # Creating a parser for each sub-sub-command
            #         # [control start/stop]
            #         innerparser.add_parser(subcommand, help=subcommand_help)

            suboptions = options.get('suboptions', {}).items()
            for option_name, suboptions in suboptions:
                self.add_parser_argument(subparse, option_name, suboptions)

        # ##########################
        # Print usage if no arguments provided
        if len(args) == 1:
            parser.print_help()
            sys.exit(1)

        # ##########################
        # Reading input parameters

        # Partial parsing
        # https://docs.python.org/3.4/library/argparse.html#partial-parsing
        # Example
        # https://gist.github.com/von/949337/

        # self.current_args = parser.parse_args()
        current_args_namespace, self.remaining_args = \
            parser.parse_known_args(args[1:])
        self.current_args = vars(current_args_namespace)

        # custom commands as a separate parser
        self.extra_parser = argparse.ArgumentParser(
            description='Custom rapydo commands from your own configuration',
            add_help=False, usage='\n$ rapydo custom CUSTOM_COMMAND'
        )
        self.extra_command_parser = self.extra_parser.add_subparsers(
            title='Available custom commands',
            dest='custom', help='list of custom commands'
        )
        self.extra_command_parser.required = True

        # ##########################
        self.enable_logs()

    def add_parser_argument(self, parser, option_name, options):
        params = self.prepare_params(options)
        alias = params.pop('alias', None)
        positional = params.pop('positional', False)
        param_name = '--%s' % option_name
        if positional:
            parser.add_argument(option_name, **params)
        elif alias is None:
            parser.add_argument(param_name, **params)
        else:
            parser.add_argument(param_name, '-%s' % alias, **params)

    def enable_logs(self):
        # Log level
        key = 'DEBUG_LEVEL'
        os.environ[key] = self.current_args.get('log_level')

        if os.environ.get(key) is not None:
            from utilities.logs import get_logger
            log = get_logger(__name__)
            log.verbose("Parsed arguments: %s" % self.current_args)

    def check_args(self, args):
        # Check on format
        for element in args:
            if element.startswith('--') and '_' in element:
                raise ValueError(
                    "Wrong \"%s\" option provided.\n" % element +
                    "Arguments containing '_' are not allowed.\n" +
                    "Use '-' instead\n")
        # NOTE: the standard is to use only '-' separators for arguments
        # beware: argparse converts them into '_' when you want to retrieve

    def read_configuration(self):
        # READ MAIN FILE WITH COMMANDS AND OPTIONS
        self.parse_conf = load_yaml_file(
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

        self.host_configuration = pinit_conf.pop('project_configuration', {})

        # Mix with parse_conf
        for key, value in pinit_conf.items():
            value = pinit_conf.get(key, None)

            if value is None:
                continue

            if not isinstance(value, dict):
                # This is a first level option
                if key in self.parse_conf['options']:
                    self.parse_conf['options'][key]['default'] = value
                else:
                    print("\nUnknown parameter %s found in .projectrc\n" % key)
            else:
                # This is a second level parameter
                if key not in self.parse_conf['subcommands']:
                    print("\nUnknown command %s found in .projectrc\n" % key)
                else:
                    conf = self.parse_conf['subcommands'][key]['suboptions']
                    for subkey, subvalue in value.items():
                        if subkey in conf:
                            conf[subkey]['default'] = subvalue
                        else:
                            print("""
Unknown parameter %s/%s found in .projectrc\n
""" % (key, subkey))

    def prepare_params(self, options):

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
