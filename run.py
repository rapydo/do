#!/usr/bin/env python3
# -*- coding: utf-8 -*-

""" DO! """

from do.params import args
from do.project import read_configuration
from do.gitter import clone_submodules
from do.builds import find_and_build
from do.utils.logs import get_logger

log = get_logger(__name__)


if __name__ == '__main__':

    action = args.get('command')
    print(f"\n********************\tDO: {action}")
    # TODO: do something with the command

    # Read project configuration
    specs = read_configuration()

    frontend = specs \
        .get('variables', {}) \
        .get('python', {}) \
        .get('frontend', {}) \
        .get('enable', False)
    log.very_verbose("Frontend is %s" % frontend)

    # TODO: recover commits for each repo

    # Clone git projects
    clone_submodules(frontend)

    # Find builds
    find_and_build(
        bp=args.get('blueprint'),
        build=args.get('execute_build'),
        frontend=frontend,
    )

    # logger
    log.info("Done")
