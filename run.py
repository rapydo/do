#!/usr/bin/env python3
# -*- coding: utf-8 -*-

""" DO! """

from do.project import read_configuration
from do.params import args
from do.builds import find_and_build
from do.utils.logs import get_logger

log = get_logger(__name__)


if __name__ == '__main__':

    # Read project configuration
    specs = read_configuration()
    frontend = specs \
        .get('variables', {}) \
        .get('python', {}) \
        .get('frontend', {}) \
        .get('enable', False)
    log.info("Frontend is %s" % frontend)

    # Clone git projects
    raise NotImplementedError("Clone git repos")
    exit(1)

    # Find builds
    find_and_build(
        bp=args.get('blueprint'),
        frontend=frontend,
        build=args.get('execute_build')
    )
    # logger
    log.info("done")
