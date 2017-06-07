# -*- coding: utf-8 -*-

"""
Main App class
"""

import os.path
try:
    from rapydo.do import arguments
except SystemExit:
    raise
except BaseException as e:
    # raise
    from rapydo.utils.logs import get_logger
    log = get_logger(__name__)
    log.critical_exit("FATAL ERROR [%s]:\n\n%s" % (type(e), e))

from rapydo.utils import checks
from rapydo.utils import helpers
from rapydo.do import project
from rapydo.do import gitter
from rapydo.do import COMPOSE_ENVIRONMENT_FILE, PLACEHOLDER
from rapydo.do.builds import locate_builds
from rapydo.do.dockerizing import Dock
from rapydo.do.compose import Compose
from rapydo.do.configuration import read_yamls

from rapydo.utils.logs import get_logger

log = get_logger(__name__)


class Application(object):

    def __init__(self, args=arguments.current_args):

        self.tested_connection = False
        self.current_args = args
        self.action = self.current_args.get('action')
        self.development = self.current_args.get('development')

        if self.action is None:
            log.critical_exit("Internal misconfiguration")
        else:
            log.info("Do request: %s" % self.action)
        self.initialize = self.action == 'init'

        # Check if docker is installed
        self._check_program('docker')
        self.docker = Dock()

        # Check docker-compose version
        pack = 'compose'
        package_version = checks.check_package(pack)
        if package_version is None:
            log.critical_exit("Could not find %s" % pack)
        else:
            log.debug("(CHECKED) %s version: %s" % (pack, package_version))

        # Check if git is installed
        self._check_program('git')

        self.blueprint = self.current_args.get('blueprint')
        self.project_dir = helpers.current_dir()
        self._run()

    def _check_program(self, program):
        program_version = checks.check_executable(executable=program, log=log)
        if program_version is None:
            log.critical_exit(
                "Missing requirement.\n" +
                "Please make sure that '%s' is installed" % program
            )
        else:
            log.debug("(CHECKED) %s version: %s" % (program, program_version))
        return

    def _inspect_current_folder(self):
        """
        Since the rapydo command only works on rapydo-core or a rapydo fork
        we want to ensure that the current folder have a structure rapydo-like
        This check is only based on file existence.
        Further checks are performed later in the following steps
        """
        local_git = gitter.get_local(".")

        if local_git is None:
            log.critical_exit(
                """You are not in a git repository
\nPlease note that this command only works from inside a rapydo-like repository
Verify that you are in the right folder, now you are in: %s
                """ % (os.getcwd())
            )

        # FIXME: move in a configuration file?
        required_files = [
            'specs/project_configuration.yaml',
            'specs/defaults.yaml',
            'apis',
            'confs',
            'containers',
            'models',
            'specs',
            'swagger'
        ]

        for fname in required_files:
            if not os.path.exists(fname):
                log.critical_exit(
                    """File or folder not found %s
\nPlease note that this command only works from inside a rapydo-like repository
Verify that you are in the right folder, now you are in: %s
                    """ % (fname, os.getcwd())
                )

    def _read_specs(self):
        """ Read project configuration """

        self.specs = project.configuration(development=self.development)

        self.vars = self.specs.get('variables', {})

        self.frontend = self.vars \
            .get('frontend', {}) \
            .get('enable', False)

        log.very_verbose("Frontend is %s" % self.frontend)

    def _verify_connected(self):
        """ Check if connected to internet """

        connected = checks.check_internet()
        if not connected:
            log.critical_exit('Internet connection unavailable')
        else:
            log.debug("(CHECKED) internet connection available")
            self.tested_connection = True
        return

    def _working_clone(self, repo):

        # substitute values starting with '$$'
        myvars = {'frontend': self.frontend}
        repo = project.apply_variables(repo, myvars)

        # Is this single repo enabled?
        repo_enabled = repo.pop('if', False)
        if not repo_enabled:
            return
        else:
            repo['do'] = self.initialize

        if not self.tested_connection and self.initialize:
            self._verify_connected()

        return gitter.clone(**repo)

    def _git_submodules(self, development=False):
        """ Check and/or clone git projects """

        repos = self.vars.get('repos')
        core = repos.pop('rapydo')

        gits = {}

        if development:
            gits['main'] = gitter.get_repo(".")
        else:
            gits['main'] = gitter.upstream(
                url=core.get('online_url'),
                path=core.get('path'),
                do=self.initialize
            )

        for name, repo in sorted(repos.items()):
            gits[name] = self._working_clone(repo)

        self.gits = gits

    def _git_check_updates(self):

        for name, gitobj in self.gits.items():
            if gitobj is not None:
                gitter.check_updates(name, gitobj)

    def _read_composer(self):
        # Read necessary files
        self.services, self.files, self.base_services, self.base_files = \
            read_yamls(self.blueprint, self.frontend)
        log.debug("Confs used (with order): %s" % self.files)

    def _build_dependencies(self):
        """ Look up for builds which are depending on templates """

        ####################
        # TODO: check all builds against their Dockefile latest commit

        pass
        # log.pp(self.services)
        # exit(1)

        ####################
        # Compare builds depending on templates
        builds = locate_builds(self.base_services, self.services)

        if self.current_args.get('force_build'):
            dc = Compose(files=self.base_files)
            log.debug("Forcing rebuild for cached templates")
            dc.force_template_build(builds)
        else:
            self._verify_build_cache(builds)

    def _verify_build_cache(self, builds):

        cache = False
        if len(builds) > 0:

            dimages = self.docker.images()

            for image_tag, build in builds.items():

                if image_tag in dimages:

                    # compare dates between git and docker
                    path = os.path.join(build.get('path'), 'Dockerfile')
                    if gitter.check_file_younger_than(
                        self.gits.get('build-templates'),
                        file=path,
                        timestamp=build.get('timestamp')
                    ):
                        log.warning("cached image [%s]" % image_tag)
                        cache = True
                else:
                    if self.action == 'check':
                        log.critical_exit(
                            """Missing template build for %s
\nSuggestion: execute the init command
                            """ % build['service'])
                    else:
                        log.debug(
                            "Missing template build for%s" % build['service'])
                        dc = Compose(files=self.base_files)
                        dc.force_template_build(builds={image_tag: build})

            if cache:
                log.info(
                    "To build cached template(s) add option \"%s %s\"" %
                    ('--force_build', str(True))
                )

        if not cache:
            log.debug("(CHECKED) no cache builds")

    def _get_services(self, key='services', sep=',',
                      default=None, avoid_default=False):

        value = self.current_args.get(key).split(sep)
        if avoid_default or default is not None:
            config_default = \
                arguments.parse_conf.get('options', {}) \
                .get('services') \
                .get('default')
            if value == [config_default]:
                if avoid_default:
                    log.critical_exit("You must set '--services' option")
                elif default is not None:
                    value = default
                else:
                    pass
        return value

    def _make_env(self):

        envfile = os.path.join(self.project_dir, COMPOSE_ENVIRONMENT_FILE)
        if self.current_args.get('force_env'):
            try:
                os.unlink(envfile)
                log.debug("Removed cache of %s" % COMPOSE_ENVIRONMENT_FILE)
            except FileNotFoundError:
                log.verbose("No %s to be removed" % COMPOSE_ENVIRONMENT_FILE)

        if not os.path.isfile(envfile):
            with open(envfile, 'w+') as whandle:
                env = self.vars.get('env')
                env['PROJECT_DOMAIN'] = self.current_args.get('hostname')
                env.update({'PLACEHOLDER': PLACEHOLDER})

                for key, value in sorted(env.items()):
                    if value is None:
                        value = ''
                    else:
                        value = str(value)
                    # log.print("ENV values. %s:*%s*" % (key, value))
                    if ' ' in value:
                        value = "'%s'" % value
                    whandle.write("%s=%s\n" % (key, value))
                log.info("Created %s file" % COMPOSE_ENVIRONMENT_FILE)
        else:
            log.debug("(CHECKED) %s already exists" % COMPOSE_ENVIRONMENT_FILE)

            # Stat file
            mixed_env = os.stat(envfile)

            # compare blame commit date against file modification date
            if gitter.check_file_younger_than(
                self.gits.get('main'),
                file='specs/defaults.yaml',
                timestamp=mixed_env.st_mtime
            ):
                log.warning(
                    "%s seems outdated. " % COMPOSE_ENVIRONMENT_FILE +
                    "Add --force_env to update."
                )

    def _check_placeholders(self):

        self.services_dict, self.active_services = \
            project.find_active(self.services)

        if len(self.active_services) == 0:
            log.critical_exit(
                """You have no active service
\nSuggestion: to activate a top-level service edit your compose yaml
and add the variable "ACTIVATE: 1" in the service enviroment
                """)
        else:
            log.info("Active services: %s" % self.active_services)

        missing = []
        for service_name in self.active_services:
            service = self.services_dict.get(service_name)

            for key, value in service.get('environment', {}).items():
                if PLACEHOLDER in str(value):
                    missing.append(key)

        if len(missing) > 0:
            log.critical_exit(
                "Missing critical params for configuration:\n%s" % missing)
        else:
            log.debug("(CHECKED) no PLACEHOLDER variable to be replaced")

        return missing

    ################################
    # ### COMMANDS
    ################################

    def check(self):

        # NOTE: a SECURITY BUG?
        # dc = Compose(files=self.files)
        # for container in dc.get_handle().project.containers():
        #     log.pp(container.client._auth_configs)
        #     exit(1)

        log.info("All checked")

    def init(self):
        log.info("Project initialized")

    def status(self):
        dc = Compose(files=self.files)
        dc.command('ps', {'-q': None})

    def clean(self):
        dc = Compose(files=self.files)
        rm_volumes = self.current_args.get('rm_volumes', False)
        options = {
            '--volumes': rm_volumes,
            '--remove-orphans': None,
            '--rmi': 'local',  # 'all'
        }
        dc.command('down', options)

    def control(self):

        command = self.current_args.get('controlcommand')
        services = self._get_services(default=self.active_services)

        dc = Compose(files=self.files)
        options = {}

        if command == 'start':
            # print("SERVICES", services)
            options = {
                '--no-deps': False,
                '-d': True,
                '--abort-on-container-exit': False,
                '--remove-orphans': False,
                '--no-recreate': False,
                '--force-recreate': False,
                '--build': False,
                '--no-build': False,
                '--scale': {},
                'SERVICE': services
            }
            command = 'up'

        elif command == 'stop':
            pass
        elif command == 'restart':
            pass
        elif command == 'remove':
            dc.command('stop')
            options = {
                # '--stop': True,  # BUG? not working
                '--force': True,
                '-v': False,  # dangerous?
                'SERVICE': []
            }
            command = 'rm'
        elif command == 'toggle_freeze':

            command = 'pause'
            for container in dc.get_handle().project.containers():

                # WOW
                # for key, value in container.dictionary.items():
                #     print("TEST", container, key, value)

                if container.dictionary.get('State').get('Status') == 'paused':
                    command = 'unpause'
                    break

        else:
            log.critical_exit("Unknown")

        dc.command(command, options)

    def log(self):
        dc = Compose(files=self.files)
        services = self._get_services(default=self.active_services)

        options = {
            # '--follow': True,
            '--follow': False,
            '--tail': 'all',
            '--no-color': False,
            '--timestamps': None,
            'SERVICE': services,
        }

        try:
            dc.command('logs', options)
        except KeyboardInterrupt:
            log.info("Stopped by keyboard")
            pass

    def shell(self, user=None, command=None, service=None):

        dc = Compose(files=self.files)

        if service is None:
            services = self._get_services(avoid_default=True)

            if len(services) != 1:
                log.critical_exit(
                    "Commands can be executed only on one service." +
                    "\nCurrent request on: %s" % services)
            else:
                service = services.pop()

        if user is None:
            user = self.current_args.get('user')

        if command is None:
            command = self.current_args.get('command', 'whoami')

        # The command must be splitted into command + args_array
        pieces = command.split()
        try:
            shell_command = pieces[0]
            shell_args = pieces[1:]
        except IndexError:
            # no command, use default
            shell_command = None
            shell_args = []
        else:
            log.info("Command request: %s(%s+%s)"
                     % (service.upper(), shell_command, shell_args))

        if service == 'restclient':
            # NOTE: an api client requires a run for an isolated service
            options = {
                'SERVICE': service,
                'COMMAND': shell_command,
                'ARGS': shell_args,
                '--name': None,
                '--user': user,
                '--rm': True,
                '--no-deps': True,
                '--service-ports': False,
                '-d': False,
                '-T': False,
                '--workdir': None,
                '-e': None,
                '--entrypoint': None,
                '--volume': [],
                '--publish': [],
            }
            dc.command('run', options)

        else:
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
            dc.command('exec_command', options)

    def build(self):
        dc = Compose(files=self.files)
        services = self._get_services(default=self.active_services)

        options = {
            'SERVICE': services,
            # FIXME: user should be able to set the two below from cli
            '--no-cache': False,
            '--pull': False,
        }
        dc.command('build', options)

    def _custom_parse_args(self):

        # custom options from configuration file
        self.custom_commands = self.specs \
            .get('controller', {}).get('commands', {})

        if len(self.custom_commands) < 1:
            log.critical_exit("No custom commands defined")

        for name, custom in self.custom_commands.items():
            arguments.extra_command_parser.add_parser(
                name, help=custom.get('description')
            )

        if len(arguments.remaining_args) != 1:
            arguments.extra_parser.print_help()
            import sys
            sys.exit(1)

        # parse it
        self.custom_command = \
            vars(
                arguments.extra_parser.parse_args(
                    arguments.remaining_args
                )
            ).get('custom')

    def custom(self):
        log.debug("Custom command: %s" % self.custom_command)
        meta = self.custom_commands.get(self.custom_command)
        meta.pop('description', None)
        return self.shell(**meta)

    def ssl_certificate(self):

        # Use my method name in a meta programming style
        import inspect
        current_method_name = inspect.currentframe().f_code.co_name

        meta = arguments.parse_conf \
            .get('subcommands') \
            .get(current_method_name, {}) \
            .get('container_exec', {})

        # Verify all is good
        assert meta.pop('name') == 'letsencrypt'

        return self.shell(**meta)

    ################################
    # ### RUN ONE COMMAND OFF
    ################################

    def _run(self):
        """ RUN THE APPLICATION

        The heart of the app: it runs a single controller command.
        """

        # NOTE: Argument are parsed inside the __init__ method

        # Initial inspection
        self._inspect_current_folder()
        self._read_specs()  # Should be the first thing

        # Generate and get the extra arguments in case of a custom command
        if self.action == 'custom':
            self._custom_parse_args()

        # Verify if we implemented the requested command
        func = getattr(self, self.action, None)
        if func is None:
            log.critical_exit("Command not yet implemented: %s" % self.action)

        # GIT related
        self._git_submodules(development=self.development)
        # FIXME: does not work with branches @mdantonio
        # self._git_check_updates()

        # Compose services and variables
        self._make_env()
        self._read_composer()
        self._check_placeholders()

        # Build or check template containers images
        self._build_dependencies()

        # Final step, launch the command
        func()
