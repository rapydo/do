# -*- coding: utf-8 -*-

"""
Integration with Docker compose

# NOTE: A way to silence compose output:
https://stackoverflow.com/questions/2828953/silence-the-stdout-of-a-function-in-python-without-trashing-sys-stdout-and-resto
"""

import compose.cli.errors as cerrors
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
        # log.very_verbose(f"Client compose '{self.project_name}': {files}")
        log.very_verbose("Client compose %s: %s" % (self.project_name, files))

    def config(self):
        _, services_list, _, _, _ = \
            get_config_from_options('.', self.options)
        # log.pp(services_list)
        return services_list

    def get_handle(self):
        # TODO: check if this might be moved into __init__
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
        except cerrors.UserError as e:
            log.critical_exit("Failed command execution:\n%s" % e)
        else:
            log.very_verbose("Executed compose %s w/%s" % (command, options))
