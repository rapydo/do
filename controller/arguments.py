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
from controller import __version__, PROJECTRC, PROJECTRC_ALTERNATIVE
from controller.conf_utilities import load_yaml_file
from controller import log


class ArgParser:
    def __init__(self, args=None):
        if args is None:
            args = sys.argv

        self.current_args = {}
        self.host_configuration = {}
        # This method can raise ValueErrors
        self.check_args(args)

        # This method saves configuration objects in self
        self.read_configuration()

        options = sorted(self.parse_conf.get('options', {}).items())
        commands = sorted(self.parse_conf.get('subcommands', {}).items())

        # Arguments definition
        parser = argparse.ArgumentParser(
            prog=args[0],
            formatter_class=lambda prog: argparse.HelpFormatter(
                prog, width=90, max_help_position=30
            )
        )
        parser._optionals.title = "Options"

        for option_name, options in options:
            self.add_parser_argument(parser, option_name, options)

        version_string = 'rapydo version {}'.format(__version__)
        parser.add_argument('--version', action='version', version=version_string)

        # Sub-parser of commands [check, init, etc]
        subparsers = parser.add_subparsers(dest='action', title='Commands')
        subparsers.required = True

        for command_name, options in commands:

            # Creating a parser for each sub-command [check, init, etc]
            subparse = subparsers.add_parser(
                command_name, help=options.get('description')
            )

            suboptions = options.get('suboptions', {}).items()
            for option_name, suboptions in suboptions:
                self.add_parser_argument(subparse, option_name, suboptions)

        if len(args) == 1:
            parser.print_help()
            sys.exit(1)

        current_args_namespace, self.remaining_args = parser.parse_known_args(args[1:])
        self.current_args = vars(current_args_namespace)

        # custom commands as a separate parser
        self.extra_parser = argparse.ArgumentParser(
            description='Custom rapydo commands from your own configuration',
            add_help=False,
            usage='\n$ rapydo custom CUSTOM_COMMAND',
        )
        self.extra_command_parser = self.extra_parser.add_subparsers(
            title='Available custom commands',
            dest='custom',
            help='list of custom commands',
        )
        self.extra_command_parser.required = True

        log.verbose("Parsed arguments: {}", self.current_args)

    def add_parser_argument(self, parser, option_name, options):
        params = self.prepare_params(options)
        alias = params.pop('alias', None)
        positional = params.pop('positional', False)
        param_name = '--{}'.format(option_name)
        if positional:
            parser.add_argument(option_name, **params)
        elif alias is None:
            parser.add_argument(param_name, **params)
        else:
            parser.add_argument(param_name, '-{}'.format(alias), **params)

    @staticmethod
    def check_args(args):
        # Check on format
        for element in args:
            if element.startswith('--') and '_' in element:
                raise ValueError(
                    "Wrong \"{}\" option provided.\n".format(element)
                    + "Arguments containing '_' are not allowed.\n"
                    + "Use '-' instead\n"
                )
        # NOTE: the standard is to use only '-' separators for arguments
        # beware: argparse converts them into '_' when you want to retrieve

    def read_configuration(self):
        # READ MAIN FILE WITH COMMANDS AND OPTIONS

        self.parse_conf = load_yaml_file(
            'argparser.yaml', path=os.path.dirname(os.path.realpath(__file__))
        )

        try:
            # READ PROJECT INIT FILE: .projectrc
            pinit_conf = load_yaml_file(
                PROJECTRC, path=os.curdir, is_optional=True)
            # Allow alternative for PROJECT INIT FILE: .project.yml
            if len(pinit_conf) < 1:
                pinit_conf = load_yaml_file(
                    PROJECTRC_ALTERNATIVE, path=os.curdir, is_optional=True)
        except AttributeError as e:
            log.exit(e)

        self.host_configuration = pinit_conf.pop('project_configuration', {})

        # Mix with parse_conf
        for key, value in pinit_conf.items():
            # value = pinit_conf.get(key, None)

            if value is None:
                continue

            if not isinstance(value, dict):
                # This is a first level option
                if key in self.parse_conf['options']:
                    self.parse_conf['options'][key]['default'] = value
                else:
                    print("\nUnknown parameter {} found in {}\n".format(key, PROJECTRC))
            else:
                # This is a second level parameter
                if key not in self.parse_conf['subcommands']:
                    print("\nUnknown command {} found in {}\n".format(key, PROJECTRC))
                else:
                    conf = self.parse_conf['subcommands'][key]['suboptions']
                    for subkey, subvalue in value.items():
                        if subkey in conf:
                            conf[subkey]['default'] = subvalue
                        else:
                            print("Unknown parameter {}/{} found in {}\n".format(
                                key, subkey, PROJECTRC))

    @staticmethod
    def prepare_params(options):

        pconf = {}
        default = options.get('default')
        pconf['default'] = default

        myhelp = "{} [default: {}]".format(options.get('help'), default)
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
