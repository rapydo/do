# -*- coding: utf-8 -*-

""" DO!

I can do things thanks to Python, YAML configurations and Docker

NOTE: the command check does nothing
"""

from do.project import project_configuration, apply_variables
from do.gitter import clone, upstream
from do.builds import find_and_build
from do.utils.logs import get_logger

log = get_logger(__name__)


class Application(object):

    def __init__(self, args):

        self.action = args.get('command')
        if self.action is None:
            raise AttributeError("Misconfiguration")
        else:
            # print(f"\n********************\tDO: {self.action}")
            print("\n********************\tDO: %s" % self.action)

        self.blueprint = args.get('blueprint')
        self.current_args = args
        self.run()

    def read_specs(self):
        """ Read project configuration """

        self.specs = project_configuration()

        self.vars = self.specs \
            .get('variables', {}) \
            .get('python', {})

        self.frontend = self.vars \
            .get('frontend', {}) \
            .get('enable', False)

        log.very_verbose("Frontend is %s" % self.frontend)

    def git_submodules(self):
        """ Check and/or clone git projects """

        initialize = self.action == 'init'
        repos = self.vars.get('repos')
        if repos is None:
            raise AttributeError(
                "Invalid configuration: repos section is missing")

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
                clone(**repo, do=initialize)

        raise NotImplementedError("TO FINISH")

    def builds(self):
        """ Look up for builds depending on templates """

        # FIXME: move here the logic
        # TODO: pass the check/init option
        find_and_build(
            bp=self.blueprint,
            frontend=self.frontend,
            build=self.current_args.get('force_build'),
        )

    def run(self):

        func = getattr(self, self.action, None)
        if func is None:
            # log.critical_exit(f"Command not yet implemented: {self.action}")
            log.critical_exit("Command not yet implemented: %s" % self.action)

        self.read_specs()

        self.git_submodules()

        self.builds()

        # Do what you're supposed to
        func()

    def check(self):
        raise AttributeError("Not completed yet")

    def init(self):
        raise AttributeError("Not completed yet")
