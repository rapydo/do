# -*- coding: utf-8 -*-

"""
Integration with Docker compose

# NOTE: A way to possibly silence compose output:
https://stackoverflow.com/questions/2828953/silence-the-stdout-of-a-function-in-python-without-trashing-sys-stdout-and-resto
"""
import os
import shlex
from compose.service import BuildError
from compose.project import NoSuchService, ProjectError
from compose.network import NetworkConfigChangedError
import compose.errors as cerrors
import compose.cli.errors as clierrors
import compose.config.errors as conferrors
from compose.cli.command import (
    get_project_name,
    get_config_from_options,
    project_from_options,
)
from compose.cli.main import TopLevelCommand
from controller import log


class Compose:

    # def __init__(self, files, options={}):
    # def __init__(self, files, net=None):
    def __init__(self, files):
        super(Compose, self).__init__()

        self.files = files
        # options.update({'--file': self.files})
        self.options = {'--file': self.files}
        # if net is not None:
        #     self.options['--net'] = net

        self.project_dir = os.curdir
        self.project_name = get_project_name(self.project_dir)
        log.verbose("Client compose {}: {}", self.project_name, files)

    def config(self):
        try:
            compose_output_tuple = get_config_from_options('.', self.options)
            # NOTE: for compatibility with docker-compose > 1.13
            # services is always the second element
            services_list = compose_output_tuple[1]
        except conferrors.ConfigurationError as e:
            log.exit("Wrong compose configuration:\n{}", e)
        else:
            return services_list

    def command(self, command, options=None, nofailure=False):

        compose_handler = TopLevelCommand(
            project_from_options(
                self.project_dir,
                self.options
            )
        )
        method = getattr(compose_handler, command)

        if options is None:
            options = {}

        if options.get('SERVICE', None) is None:
            options['SERVICE'] = []

        log.debug("docker-compose command: '{}'", command)

        out = None
        # sometimes this import stucks... importing here to avoid unnecessary waits
        from docker.errors import APIError
        try:
            out = method(options=options)
        except SystemExit as e:
            # NOTE: we check the status here.
            # System exit is received also when a normal command finished.
            if e.code < 0:
                log.warning("Invalid code returned: {}", e.code)
            elif e.code > 0:
                log.exit("Compose received: system.exit({})", e.code, error_code=e.code)
            else:
                log.verbose("Executed compose {} w/{}", command, options)
        except (clierrors.UserError, cerrors.OperationFailedError, BuildError) as e:
            msg = "Failed command execution:\n{}".format(e)
            if nofailure:
                raise AttributeError(msg)
            else:
                log.exit(msg)
        except APIError as e:
            log.exit("Failed docker container:\n{}", e)
        except (ProjectError, NoSuchService) as e:
            log.exit(str(e))
        else:
            log.verbose("Executed compose {} w/{}", command, options)

        return out

    @staticmethod
    def split_command(command):
        """
            Split a command into command + args_array
        """
        if command is None:
            return (None, [])

        # pieces = command.split()
        pieces = shlex.split(command)
        try:
            shell_command = pieces[0]
            shell_args = pieces[1:]
        except IndexError:
            # no command, use default
            shell_command = None
            shell_args = []

        return (shell_command, shell_args)

    def start_containers(
        self,
        services,
        detach=True,
        scale=None,
        skip_dependencies=False,
        abort_on_container_exit=False,
        no_recreate=False,
    ):
        """
            Start containers (docker-compose up)
        """

        if scale is None:
            scale = {}

        options = {
            'SERVICE': services,
            '--no-deps': skip_dependencies,
            '--detach': detach,
            '--build': None,
            '--no-color': False,
            '--remove-orphans': False,
            '--abort-on-container-exit': abort_on_container_exit,
            '--no-recreate': no_recreate,
            '--force-recreate': False,
            '--always-recreate-deps': False,
            '--no-build': False,
            '--scale': scale,
        }

        try:
            return self.command('up', options)
        except NetworkConfigChangedError as e:
            log.exit(
                "{}.\n{} ({})",
                e,
                "Remove previously created networks and try again",
                "you can use rapydo remove --networks or docker system prune"
            )

    def create_volatile_container(
        self, service, command=None, publish=None, detach=False, user=None
    ):
        """
            Execute a command on a not container
        """

        if publish is None:
            publish = []

        if len(publish) <= 0:
            service_post = True
        else:
            service_post = False

        shell_command, shell_args = self.split_command(command)

        options = {
            'SERVICE': service,
            '--publish': publish,
            '--service-ports': service_post,
            'COMMAND': shell_command,
            'ARGS': shell_args,
            '-e': [],
            '--volume': [],
            '--rm': True,
            '--no-deps': True,
            '--name': None,
            '--user': user,
            '--workdir': None,
            '--entrypoint': None,
            '--detach': detach,
            '--use-aliases': False,  # introduced with compose 1.21
            '-T': False,
            '--label': None,
        }

        return self.command('run', options)

    def exec_command(
        self, service, user=None, command=None, disable_tty=False, nofailure=False
    ):
        """
            Execute a command on a running container
        """
        shell_command, shell_args = self.split_command(command)
        options = {
            'SERVICE': service,
            'COMMAND': shell_command,
            'ARGS': shell_args,
            '--index': '1',
            '--user': user,
            '-T': disable_tty,
            '--env': None,
            '--workdir': None,
            # '-d': False,
            '--detach': False,
            '--privileged': False,
        }
        if shell_command is not None:
            log.debug(
                "Command: {}({}+{})", service.lower(), shell_command, shell_args
            )
        try:
            out = self.command('exec_command', options, nofailure=nofailure)
        except NoSuchService:
            if nofailure:
                raise AttributeError("Cannot find service: {}".format(service))
            else:
                log.exit("Cannot find a running container called {}", service)
        else:
            return out

    @staticmethod
    def command_defaults(command):
        if command in ['run']:
            return Compose.set_defaults(
                variables=[
                    'COMMAND',
                    'T',
                    'e',
                    'entrypoint',
                    'user',
                    'label',
                    'publish',
                    'service-ports',
                    'name',
                    'workdir',
                    'volume',
                    'no-deps',
                    'use-aliases',
                ],
                merge={'--rm': True},
            )
        else:
            log.exit("No default implemented for: {}", command)

    @staticmethod
    def set_defaults(variables, merge=None):
        if merge is None:
            options = {}
        else:
            options = merge
        for variable in variables:
            if len(variable) == 1:
                key = '-{}'.format(variable)
            elif variable.upper() == variable:
                key = variable
            else:
                key = '--{}'.format(variable)
            options[key] = None
        log.verbose('defaults: {}', options)
        return options
