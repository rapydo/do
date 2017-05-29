# -*- coding: utf-8 -*-

"""
Main App class
"""

from do import check_internet, check_executable, check_package
from do.arguments import current_args
from do.project import project_configuration, apply_variables
from do.gitter import clone, upstream
from do.builds import locate_builds
from do.dockerizing import Dock
from do.compose import Compose
from do.configuration import read_yamls
from do.utils.logs import get_logger

log = get_logger(__name__)


class Application(object):

    def __init__(self, args=current_args):

        self.current_args = args
        self.action = self.current_args.get('command')

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

        # Check if connected to internet
        connected = check_internet()
        if not connected:
            log.critical_exit('Internet connection unavailable')
        else:
            log.debug("(CHECKED) internet connection available")

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

    def _read_specs(self):
        """ Read project configuration """

        self.specs = project_configuration()

        self.vars = self.specs \
            .get('variables', {}) \
            .get('python', {})

        self.frontend = self.vars \
            .get('frontend', {}) \
            .get('enable', False)

        log.very_verbose("Frontend is %s" % self.frontend)

    def _git_submodules(self):
        """ Check and/or clone git projects """

        initialize = self.action == 'init'
        repos = self.vars.get('repos')
        core = repos.pop('rapydo')

        upstream(
            url=core.get('online_url'),
            path=core.get('path'),
            do=initialize
        )

        myvars = {'frontend': self.frontend}

        for _, repo in repos.items():

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

        self._read_specs()

        self._git_submodules()

        self._build_dependencies()

        # Do what you're supposed to
        func()

    def check(self):
        log.info("All checked")

    def init(self):
        log.info("Project initialized")

    def control(self):

        command = self.current_args.get('controlcommand')
        services = self.current_args.get('services').split(',')

        dc = Compose(files=self.files)

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
            dc.up(options)

        elif command == 'stop':
            dc.stop({'SERVICE': []})

        else:
            log.critical_exit("Not implemented yet")
