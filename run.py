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

from do import containers_yaml_path
from do.params import args
from do.input import read_yamls
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

if __name__ == '__main__':

    # Read necessary files
    services_data = read_yamls(args.get('blueprint'), containers_yaml_path)

    # Parse docker files for services
    for service_name, service in services_data.items():

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
