# -*- coding: utf-8 -*-

""" DO! """

from do.project import read_configuration
from do.gitter import clone_submodules
from do.builds import find_and_build
from do.utils.logs import get_logger

log = get_logger(__name__)


class Application(object):

    def __init__(self, args):

        self.action = args.get('command')
        if self.action is None:
            raise AttributeError("Misconfiguration")
        else:
            print(f"\n********************\tDO: {self.action}")

        self.blueprint = args.get('blueprint')
        self.force_build = args.get('force_build')

        self.run()

    def run(self):

        # Read project configuration
        specs = read_configuration()

        frontend = specs \
            .get('variables', {}) \
            .get('python', {}) \
            .get('frontend', {}) \
            .get('enable', False)
        log.very_verbose("Frontend is %s" % frontend)

        # TODO: recover commits for each subrepo
        # and check against online version

        # Clone git projects
        clone_submodules(frontend)

        # Find builds
        find_and_build(
            bp=self.blueprint,
            build=self.force_build,
            frontend=frontend,
        )

        # TODO: do something with the command
        func = getattr(self, self.action, None)
        if func is None:
            log.critical_exit(f"Command not yet implemented: {self.action}")
        else:
            func()
