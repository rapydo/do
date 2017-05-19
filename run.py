#!/usr/bin/env python3
# -*- coding: utf-8 -*-

""" DO! """

# import sys
# sys.path.append("/Users/projects/tmp/do")
import os

from dockerfile_parse import DockerfileParser
# https://github.com/DBuildService/dockerfile-parse

import docker
# https://docker-py.readthedocs.io/en/stable/

from do.utils.myyaml import load_yaml_file
from do.params import args
from do.utils.logs import get_logger

##########################
log = get_logger(__name__)

##########################
docker
# # Use docker client
# client = docker.from_env()
# containers = client.containers.list()
# log.debug("Docker:%s" % containers)

##########################
# Read YAML files
containers_yaml_path = os.path.join(os.curdir, 'containers')
try:
    compose = load_yaml_file(
        file=args.get('blueprint'),
        extension='yml',
        path=containers_yaml_path
    )
except KeyError as e:
    log.critical_exit(e)

# services_data = compose.get('services', {})
# services_list = list(services_data.keys())
# log.debug("Services:\n%s" % services_list)

if __name__ == '__main__':

    # Parse docker files for services
    for service_name, service in compose.get('services', {}).items():

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

    log.info("Completed")
