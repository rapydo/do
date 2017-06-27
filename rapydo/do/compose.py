# -*- coding: utf-8 -*-

"""
Integration with Docker compose

# NOTE: A way to possibly silence compose output:
https://stackoverflow.com/questions/2828953/silence-the-stdout-of-a-function-in-python-without-trashing-sys-stdout-and-resto
"""

from rapydo.do.dockerizing import docker_errors
import compose.service
import compose.errors as cerrors
import compose.cli.errors as clierrors
import compose.config.errors as conferrors
from compose.cli.command import \
    get_project_name, get_config_from_options, project_from_options
from compose.cli.main import TopLevelCommand
from rapydo.utils import helpers
from rapydo.utils.logs import get_logger

log = get_logger(__name__)


class Compose(object):

    def __init__(self, files, options={}):
        super(Compose, self).__init__()

        self.files = files
        options.update({'--file': self.files})
        self.options = options

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

    def force_template_build(self, builds, options={}):

        compose_handler = self.get_handle()
        force_options = {
            '--no-cache': True,
            '--pull': True,
        }

        for image_tag, build in builds.items():

            service = build.get('service')
            log.verbose("Building template for: %s" % service)

            # myoptions = {'SERVICE': [service], **force_options, **options}
            options.update(force_options)
            options.update({'SERVICE': [service]})

            compose_handler.build(options=options)
            log.info("Built template: %s" % service)

        return

    def command(self, command, options={}):

        compose_handler = self.get_handle()
        method = getattr(compose_handler, command)

        if options.get('SERVICE', None) is None:
            options['SERVICE'] = []

        log.info("Requesting within compose: '%s'" % command)
        try:
            method(options=options)
        except (
            clierrors.UserError,
            cerrors.OperationFailedError,
            compose.service.BuildError,
        ) as e:
            log.critical_exit("Failed command execution:\n%s" % e)
        except docker_errors as e:
            log.critical_exit("Failed docker container:\n%s" % e)
        else:
            log.very_verbose("Executed compose %s w/%s" % (command, options))

    def split_command(self, command):
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

    def create_volatile_container(self, service, command=None, publish=[]):
        """
            Execute a command on a not container
        """

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
            '-d': False, '-T': False,
        }

        self.command('run', options)

    def exec_command(self, service, user=None, command=None):
        """
            Execute a command on a running container
        """

        shell_command, shell_args = self.split_command(command)
        if shell_command is not None:
            log.info("Command request: %s(%s+%s)"
                     % (service.upper(), shell_command, shell_args))

        options = {
            'SERVICE': service,
            'COMMAND': shell_command,
            'ARGS': shell_args,
            '--index': '1',
            '--user': user,
            '--privileged': True,
            '-T': False,
            '-d': False,
        }
        try:
            self.command('exec_command', options)
        except compose.project.NoSuchService:
            log.exit(
                "Cannot find a running container with this name: %s" % service)
