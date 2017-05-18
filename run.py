#!/usr/bin/env python3
# -*- coding: utf-8 -*-

""" DO! """

import sys
sys.path.append("/Users/projects/tmp/do")

from do.utils.myyaml import load_yaml_file
from do.utils.logs import get_logger

from dockerfile_parse import DockerfileParser
# https://github.com/DBuildService/dockerfile-parse

import docker
# https://docker-py.readthedocs.io/en/stable/

##########################
SOME_FILE = "/Users/projects/tmp/custom/containers/debug.yml"
log = get_logger(__name__)

##########################
# Use docker client
client = docker.from_env()
containers = client.containers.list()
log.debug("Docker:%s" % containers)

##########################
# Read YAML files
compose = load_yaml_file(SOME_FILE)
services_data = compose.get('services', {})
services_list = list(services_data.keys())
log.debug("Services:\n%s" % services_list)

##########################
# Parse docker files
dfp = DockerfileParser()
# dfp = DockerfileParser('Dockerfile')
# dfp.content
# dfp.baseimage
log.debug("Parse dockerfile")

##########################
log.info("Completed")
