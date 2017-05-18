#!/usr/bin/env python3
# -*- coding: utf-8 -*-

""" DO! """

import os
import sys
import argparse
sys.path.append("/Users/projects/tmp/do")

from do.utils.myyaml import load_yaml_file
from do.utils.logs import get_logger

from dockerfile_parse import DockerfileParser
# https://github.com/DBuildService/dockerfile-parse

# import docker
# https://docker-py.readthedocs.io/en/stable/

##########################
log = get_logger(__name__)

##########################
# Arguments definition
parser = argparse.ArgumentParser(
    prog='do', description='Do things on this project'
)
parser.add_argument(
    '--project', type=str, metavar='PROJECT_NAME', default='vanilla',
    help='Your project name which forked RAPyDo core as vanilla customization')
parser.add_argument(
    '--blueprint', type=str, metavar='CONTAINERS_YAML_BLUEPRINT',
    required=True,
    help='Blueprint marker of the configuration to launch')

# Reading input parameters
args = parser.parse_args()
args = vars(args)
log.very_verbose("Parsed args: %s" % args)

# ##########################
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

##########################
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

##########################
if __name__ == '__main__':
    log.info("Completed")
