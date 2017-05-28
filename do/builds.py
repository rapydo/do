# -*- coding: utf-8 -*-

"""
Parse dockerfiles and check for builds

# https://github.com/DBuildService/dockerfile-parse
# https://docker-py.readthedocs.io/en/stable/
"""

import os
from dockerfile_parse import DockerfileParser
from do import containers_yaml_path
from do.utils.logs import get_logger

log = get_logger(__name__)


def find_templates_build(base_services):

    templates = {}

    for base_service in base_services:

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
                    'path': template_build.get('context')
                }

    return templates


def find_overriden_templates(services, templates={}):

    builds = {}

    for service in services:

        builder = service.get('build')
        if builder is not None:

            dpath = builder.get('context')
            dockerfile = os.path.join(containers_yaml_path, dpath)
            dfp = DockerfileParser(dockerfile)

            try:
                dfp.content
                log.very_verbose("Parsed dockerfile %s" % dpath)
            except FileNotFoundError as e:
                log.critical_exit(e)

            if dfp.baseimage.endswith(':template'):
                if dfp.baseimage not in templates:
                    log.critical_exit(
                        "Template build misconfiguration with: %s"
                        % service.get('name')
                    )
                else:
                    builds[dfp.baseimage] = templates.get(dfp.baseimage)

    return builds


def locate_builds(base_services, services):

    # 1. find templates and store them
    templates = find_templates_build(base_services)

    # 2. find templates that were overridden
    return find_overriden_templates(services, templates)
