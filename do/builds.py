# -*- coding: utf-8 -*-

"""
Parse dockerfiles and check for builds

# https://github.com/DBuildService/dockerfile-parse
# https://docker-py.readthedocs.io/en/stable/
"""

import os
import docker
from dockerfile_parse import DockerfileParser
from do.compose import Compose
from do import containers_yaml_path
from do.configuration import read_yamls
from do.utils.logs import get_logger

log = get_logger(__name__)


def docker_images():
    client = docker.from_env()
    images = []
    for obj in client.images.list():
        for tag in obj.attrs.get('RepoTags', []):
            images.append(tag)
    # log.debug("Docker:%s" % images)
    return images

# def some_docker():
#     client = docker.from_env()
#     containers = client.containers.list()
#     log.debug("Docker:%s" % containers)


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


def find_and_build(bp, build=False, frontend=False):

    # Read necessary files
    services, files, base_services, base_files = read_yamls(bp, frontend)
    # log.debug(f"Confs used in order: {files}")
    log.debug("Confs used in order: %s" % files)

    # 1. find templates and store them
    templates = find_templates_build(base_services)

    # 2. find templates that were overridden
    builds = find_overriden_templates(services, templates)

    # 3. templates to be built (if requested)
    if len(builds) > 0:

        if build:
            dc = Compose(
                files=base_files,
            )
            dc.force_template_build(builds)
        else:
            dimages = docker_images()
            cache = False
            for image_tag, build in builds.items():

                # TODO: BETTER CHECK: compare dates between git and docker;
                # check if build template commit (git.blame) is older
                # than image build datetime.
                # SEE gitter.py

                if image_tag in dimages:
                    log.warning(
                        "Notice: using cache for image [%s]" % image_tag)
                    cache = True
            if cache:
                log.info(
                    "If you want to build these template(s) " +
                    "add option \"%s %s\"" % ('--execute_build', str(True))
                )

    return
