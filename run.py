#!/usr/bin/env python3
# -*- coding: utf-8 -*-

""" DO! """

import sys
sys.path.append("/Users/projects/tmp/do")

from do.utils.myyaml import load_yaml_file
from do.utils.logs import get_logger

from dockerfile_parse import DockerfileParser
# https://github.com/DBuildService/dockerfile-parse

##########################
SOME_FILE = "/Users/projects/tmp/rapydo/containers/debug.yml"
log = get_logger(__name__)

##########################
compose = load_yaml_file(SOME_FILE)
services_data = compose.get('services', {})
services_list = list(services_data.keys())
log.debug("Services:\n%s" % services_list)

##########################
dfp = DockerfileParser()
# dfp = DockerfileParser('Dockerfile')
# dfp.content
# dfp.baseimage
log.debug("Parse dockerfile")

##########################
log.info("Completed")
