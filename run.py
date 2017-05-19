#!/usr/bin/env python3
# -*- coding: utf-8 -*-

""" DO! """

# import sys
# sys.path.append("/Users/projects/tmp/do")

import docker
# https://docker-py.readthedocs.io/en/stable/

from do import containers_yaml_path
from do.params import args
from do.input import read_yamls
from do.builds import find_and_build
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
    # Find builds
    find_and_build(services_data)
    # logger
    log.info("Completed")
