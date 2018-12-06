# -*- coding: utf-8 -*-

"""
Integration with Docker compose

# NOTE: A way to possibly silence compose output:
https://stackoverflow.com/questions/2828953/silence-the-stdout-of-a-function-in-python-without-trashing-sys-stdout-and-resto
"""

from controller.dockerizing import docker_errors
from compose.service import BuildError
from compose.project import NoSuchService, ProjectError
import compose.errors as cerrors
import compose.cli.errors as clierrors
import compose.config.errors as conferrors
from compose.cli.command import \
    get_project_name, get_config_from_options, project_from_options
from compose.cli.main import TopLevelCommand
from utilities import helpers
from utilities.logs import get_logger

log = get_logger(__name__)

compose_log = 'docker-compose command: '


class Compose(object):

    # def __init__(self, files, options={}):
    # def __init__(self, files, net=None):
    def __init__(self, files):
        super(Compose, self).__init__()

        self.files = files
        # options.update({'--file': self.files})
        self.options = {'--file': self.files}
        # if net is not None:
        #     self.options['--net'] = net

        self.project_dir = helpers.current_dir()
        self.project_name = get_project_name(self.project_dir)
        log.very_verbose("Client compose %s: %s" % (self.project_name, files))

    def config(self):
        try:
            compose_output_tuple = get_config_from_options('.', self.options)
            # NOTE: for compatibility with docker-compose > 1.13
            # services is always the second element
            services_list = compose_output_tuple[1]
        except conferrors.ConfigurationError as e:
            log.critical_exit("Wrong compose configuration:\n%s" % e)
        else:
            return services_list

    def get_handle(self):
        return TopLevelCommand(
            project_from_options(self.project_dir, self.options))

    def build_images(self, builds, force_pull=True,
                     current_version=None, current_uid=None):

        try:
            compose_handler = self.get_handle()

            for image, build in builds.items():

                service = build.get('service')
                log.verbose("Building image: %s" % image)

                options = {
                    '--no-cache': True,
                    '--pull': force_pull,
                    'SERVICE': [service]
                }

                build_args = []
                # NOTE: we can set only 1 variable since options is a dict
                if current_version is not None:
                    build_args.append(
                        "%s=%s" % ("RAPYDO_VERSION", current_version))
                if current_uid is not None:
                    build_args.append(
                        "%s=%s" % ("CURRENT_UID", current_uid))

                if len(build_args) > 0:
                    options['--build-arg'] = build_args

                compose_handler.build(options=options)
                log.info("Built image: %s" % image)

            return
        except SystemExit:
            log.info("SystemExit during template building")

    def command(self, command, options=None, nofailure=False):

        # NOTE: debug defaults
        # tmp = self.get_defaults(command)
        # print("TEST", tmp, type(tmp))
        # # exit(1)

        compose_handler = self.get_handle()
        method = getattr(compose_handler, command)

        if options is None:
            options = {}

        if options.get('SERVICE', None) is None:
            options['SERVICE'] = []

        log.debug("%s'%s'" % (compose_log, command))

        out = None
        try:
            out = method(options=options)
        except SystemExit as e:
            # NOTE: we check the status here.
            # System exit is received also when a normal command finished.
            if e.code < 0:
                log.warning("Invalid code returned: %s", e.code)
            elif e.code > 0:
                log.warning("Compose received: system.exit(%s)", e.code)
                log.exit(error_code=e.code)
            else:
                log.very_verbose(
                    "Executed compose %s w/%s" % (command, options))
        except (
            clierrors.UserError,
            cerrors.OperationFailedError,
            BuildError,
        ) as e:
            msg = "Failed command execution:\n%s" % e
            if nofailure:
                raise AttributeError(msg)
            else:
                log.critical_exit(msg)
        except docker_errors as e:
            log.critical_exit("Failed docker container:\n%s" % e)
        except ProjectError as e:
            log.exit(str(e))
        else:
            log.very_verbose("Executed compose %s w/%s" % (command, options))

        return out

    @staticmethod
    def split_command(command):
        """
            Split a command into command + args_array
        """
        if command is None:
            return (None, [])

        pieces = command.split()
        try:
            shell_command = pieces[0]
            shell_args = pieces[1:]
        except IndexError:
            # no command, use default
            shell_command = None
            shell_args = []

        return (shell_command, shell_args)

    def create_volatile_container(self, service, command=None, publish=None):
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
            '--publish': publish, '--service-ports': service_post,
            'COMMAND': shell_command,
            'ARGS': shell_args,
            '-e': [], '--volume': [],
            '--rm': True, '--no-deps': True,
            '--name': None, '--user': None,
            '--workdir': None, '--entrypoint': None,
            # '-d': False,
            '--detach': False,
            '--use-aliases': False,  # introduced with compose 1.21
            '-T': False,
            '--label': None,
        }

        return self.command('run', options)

    def exec_command(self, service, user=None, command=None, nofailure=False):
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
            '-T': False,
            '--env': None,
            '--workdir': None,
            # '-d': False,
            '--detach': False,
            '--privileged': False,
        }
        if shell_command is not None:
            log.debug("Command: %s(%s+%s)"
                      % (service.lower(), shell_command, shell_args))
        try:
            out = self.command('exec_command', options, nofailure=nofailure)
        except NoSuchService:
            if nofailure:
                raise AttributeError("Cannot find service: %s", service)
            else:
                log.exit("Cannot find a running container called %s" % service)
        else:
            return out

    @staticmethod
    def command_defaults(command):
        if command in ['run']:
            return Compose.set_defaults(
                variables=[
                    'COMMAND', 'T', 'e',
                    'entrypoint', 'user', 'label', 'publish', 'service-ports',
                    'name', 'workdir', 'volume', 'no-deps', 'use-aliases'
                ],
                merge={'--rm': True}
            )
        else:
            log.exit("No default implemented for: %s", command)

    @staticmethod
    def set_defaults(variables, merge=None):
        if merge is None:
            options = {}
        else:
            options = merge
        for variable in variables:
            if len(variable) == 1:
                key = '-' + variable
            elif variable.upper() == variable:
                key = variable
            else:
                key = '--' + variable
            options[key] = None
        log.very_verbose('defaults: %s', options)
        return options
