# -*- coding: utf-8 -*-
from glom import glom
from controller.compose import Compose
from controller import log


def __call__(arguments, files, specs, **kwargs):

    # custom options from configuration file
    custom_commands = glom(specs, "controller.commands", default={})

    if len(custom_commands) < 1:
        log.exit("No custom commands defined")

    for name, custom in custom_commands.items():
        arguments.extra_command_parser.add_parser(
            name, help=custom.get('description')
        )

    if len(arguments.remaining_args) != 1:
        arguments.extra_parser.print_help()

        log.exit("Errors with parser configuration")

    # parse it
    custom_command = vars(
        arguments.extra_parser.parse_args(arguments.remaining_args)
    ).get('custom')

    log.debug("Custom command: {}", custom_command)
    meta = custom_commands.get(custom_command)
    meta.pop('description', None)

    service = meta.get('service')
    user = meta.get('user', None)
    command = meta.get('command', None)
    dc = Compose(files=files)
    return dc.exec_command(service, user=user, command=command)
