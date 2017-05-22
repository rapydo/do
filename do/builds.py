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
from do.utils.logs import get_logger

log = get_logger(__name__)


def some_docker():
    client = docker.from_env()
    containers = client.containers.list()
    log.debug("Docker:%s" % containers)


def find_and_build(services={}):

    # Parse docker files for services
    for service_name, service in services.items():

        builder = service.get('build')
        if builder is not None:

            dockerfile = os.path.join(containers_yaml_path, builder)
            dfp = DockerfileParser(dockerfile)

            try:
                dfp.content
                log.debug("Parsed dockerfile %s" % builder)
            except FileNotFoundError as e:
                log.critical_exit(e)

            if dfp.baseimage.endswith(':template'):
                log.warning("To build: %s" % dfp.baseimage)

    return
