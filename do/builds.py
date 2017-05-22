# -*- coding: utf-8 -*-

"""
Parse dockerfiles and check for builds

# https://github.com/DBuildService/dockerfile-parse
# https://docker-py.readthedocs.io/en/stable/
"""

import os
import docker
from dockerfile_parse import DockerfileParser
from do import containers_yaml_path
from do.input import read_yamls
from do.utils.logs import get_logger

log = get_logger(__name__)


def some_docker():
    client = docker.from_env()
    containers = client.containers.list()
    log.debug("Docker:%s" % containers)


def find_templates_build(base_services):

    templates = {}

    for base_service in base_services:

        template_build = base_service.get('build')

        if template_build is not None:

            template_name = base_service.get('name')
            template_image = base_service.get('image')

            if template_image is None:
                raise AttributeError(
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

    for service in services:

        builder = service.get('build')
        if builder is not None:

            dockerfile = os.path.join(
                containers_yaml_path,
                builder.get('context'))
            dfp = DockerfileParser(dockerfile)

            try:
                dfp.content
                log.debug("Parsed dockerfile %s" % builder)
            except FileNotFoundError as e:
                log.critical_exit(e)

            if dfp.baseimage.endswith(':template'):
                if dfp.baseimage not in templates:
                    log.critical_exit(
                        "Template build misconfiguration with: %s"
                        % service.get('name')
                    )

                print(
                    "TO BUILD:\n",
                    dfp.baseimage, templates.get(dfp.baseimage))

    print("DEBUG")
    exit(1)


def find_and_build(bp):

    # Read necessary files
    services, base_services = read_yamls(bp)

    # 1. find templates and store them
    templates = find_templates_build(base_services)

    # 2. find templates that were overridden
    find_overriden_templates(services, templates)

    # 3. (outside loop) find templates to be built
    print("DEBUG STEP 3")
    exit(1)

    # 4. build if requested
    pass

    return
