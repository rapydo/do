# -*- coding: utf-8 -*-

"""
Parse dockerfiles and check for builds

# https://github.com/DBuildService/dockerfile-parse
# https://docker-py.readthedocs.io/en/stable/
"""

from dockerfile_parse import DockerfileParser
from rapydo.utils import CONTAINERS_YAML_DIRNAME
from rapydo.do.dockerizing import Dock
from rapydo.utils import helpers
from rapydo.utils.logs import get_logger

log = get_logger(__name__)


def find_templates_build(base_services):

    templates = {}
    docker = Dock()

    for base_service in base_services:

        # log.pp(base_service)
        template_build = base_service.get('build')

        if template_build is not None:

            template_name = base_service.get('name')
            template_image = base_service.get('image')

            if template_image is None:
                log.critical_exit(
                    "Error with template build: %s\n"
                    "Template builds must have a name!"
                    % template_name
                )
            else:
                templates[template_image] = {
                    'service': template_name,
                    'path': template_build.get('context'),
                    'timestamp': docker.image_attribute(template_image)
                }

    return templates


def find_overriden_templates(services, templates={}):

    builds = {}

    for service in services:

        builder = service.get('build')
        if builder is not None:

            dpath = builder.get('context')
            dockerfile = helpers.current_dir(CONTAINERS_YAML_DIRNAME, dpath)
            dfp = DockerfileParser(dockerfile)

            try:
                dfp.content
                log.very_verbose("Parsed dockerfile %s" % dpath)
            except FileNotFoundError as e:
                log.critical_exit(e)

            if dfp.baseimage is None:
                dfp.baseimage = 'unknown_build'
            elif dfp.baseimage.endswith(':template'):
                if dfp.baseimage not in templates:
                    log.critical_exit(
                        """Unable to find the %s in this project
\nPlease inspect the FROM image in %s/Dockerfile
                        """ % (dfp.baseimage, dockerfile)
                    )
                else:
                    builds[dfp.baseimage] = templates.get(dfp.baseimage)

    return builds


def locate_builds(base_services, services):

    # TODO: cool progress bar in cli for the whole function START

    # 1. find templates and store them
    templates = find_templates_build(base_services)

    # 2. find templates that were overridden
    response = find_overriden_templates(services, templates)

    # TODO: cool progress bar in cli for the whole function END
    return response
