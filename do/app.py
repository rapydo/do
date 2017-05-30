# -*- coding: utf-8 -*-

"""
Main App class
"""

import os.path
from do import check_internet, check_executable, check_package
from do.arguments import current_args
from do.project import project_configuration, apply_variables
from do.gitter import clone, upstream, get_local
from do.builds import locate_builds
from do.dockerizing import Dock
from do.compose import Compose
from do.configuration import read_yamls
from do.utils.logs import get_logger

log = get_logger(__name__)


class Application(object):

    def __init__(self, args=current_args):

        self.current_args = args
        self.action = self.current_args.get('action')
        self.development = self.current_args.get('development')

        if self.action is None:
            log.critical_exit("Internal misconfiguration")
        else:
            log.info("Do request: %s" % self.action)

        # Check if docker is installed
        self._check_program('docker')
        self.docker = Dock()

        # Check docker-compose version
        pack = 'compose'
        package_version = check_package(pack)
        if package_version is None:
            log.critical_exit("Could not find %s" % pack)
        else:
            log.debug("(CHECKED) %s version: %s" % (pack, package_version))

        # Check if git is installed
        self._check_program('git')

        # TODO: git check

        self.blueprint = self.current_args.get('blueprint')
        self.run()

    def _check_program(self, program):
        program_version = check_executable(executable=program, log=log)
        if program_version is None:
            log.critical_exit('Please make sure %s is installed' % program)
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
        local_git = get_local(".")

        if local_git is None:
            log.critical_exit(
                """You are not in a git repository
\nPlease note that this command only works from inside a rapydo-like repository
Verify that you are in the right folder, now you are in: %s
                """ % (os.getcwd())
            )

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

        self.specs = project_configuration(development=self.development)

        self.vars = self.specs \
            .get('variables', {}) \
            .get('python', {})

        self.frontend = self.vars \
            .get('frontend', {}) \
            .get('enable', False)

        log.very_verbose("Frontend is %s" % self.frontend)

    def _git_submodules(self, development=False):
        """ Check and/or clone git projects """

        initialize = self.action == 'init'
        if initialize:
            # Check if connected to internet
            connected = check_internet()
            if not connected:
                log.critical_exit('Internet connection unavailable')
            else:
                log.debug("(CHECKED) internet connection available")

        repos = self.vars.get('repos')
        core = repos.pop('rapydo')

        if not development:
            upstream(
                url=core.get('online_url'),
                path=core.get('path'),
                do=initialize
            )

        myvars = {'frontend': self.frontend}

        for _, repo in sorted(repos.items()):

            # substitute $$ values
            repo = apply_variables(repo, myvars)

            if repo.pop('if', False):
                clone(do=initialize, **repo)

    def _build_dependencies(self):
        """ Look up for builds which are depending on templates """

        # Read necessary files
        self.services, self.files, self.base_services, base_files = \
            read_yamls(self.blueprint, self.frontend)
        log.debug("Confs used (with order): %s" % self.files)

        builds = locate_builds(self.base_services, self.services)

        if self.current_args.get('force_build_dependencies'):
            dc = Compose(files=base_files)
            dc.force_template_build(builds)
        else:
            self.verify_build_cache(builds)

    def verify_build_cache(self, builds):
        cache = False
        if len(builds) > 0:

            dimages = self.docker.images()
            for image_tag, build in builds.items():

                # TODO: BETTER CHECK: compare dates between git and docker;
                # check if build template commit (git.blame) is older
                # than image build datetime.
                # SEE gitter.py

                if image_tag in dimages:
                    log.warning("cached image [%s]" % image_tag)
                    cache = True
            if cache:
                log.info(
                    "To build cached template(s) add option \"%s %s\"" %
                    ('--force_build_dependencies', str(True))
                )

        if not cache:
            log.debug("(CHECKED) no cache builds")

    def run(self):

        func = getattr(self, self.action, None)
        if func is None:
            # log.critical_exit(f"Command not yet implemented: {self.action}")
            log.critical_exit("Command not yet implemented: %s" % self.action)

        self._inspect_current_folder()

        self._read_specs()

        self._git_submodules(development=self.development)

        self._build_dependencies()

        # Do what you're supposed to
        func()

    def check(self):

        # NOTE: a SECURITY BUG?
        # dc = Compose(files=self.files)
        # for container in dc.get_handle().project.containers():
        #     log.pp(container.client._auth_configs)
        #     exit(1)

        log.info("All checked")

    def get_services(self, key='services', sep=','):
        return self.current_args.get(key).split(sep)

    def init(self):
        log.info("Project initialized")

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
        services = self.get_services()

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
        services = self.get_services()
        options = {
            'SERVICE': services,
            '--follow': True,
            '--tail': 'all',
            '--no-color': False,
            '--timestamps': None,
        }
        try:
            dc.command('logs', options)
        except KeyboardInterrupt:
            log.info("Stopped by keyboard")
            pass

    def shell(self):
        dc = Compose(files=self.files)

        services = self.get_services()
        user = self.current_args.get('user')
        whole_command = self.current_args.get('command', 'whoami')

        # The command must be splitted into command + args_array
        pieces = whole_command.split()
        shell_command = pieces[0]
        shell_args = pieces[1:]

        if len(services) != 1:
            log.critical_exit(
                "Commands can be executed only on one service." +
                "\nCurrent request on: %s" % services)
        else:
            service = services.pop()
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
        dc.command('exec_command', options)
