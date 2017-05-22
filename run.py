#!/usr/bin/env python3
# -*- coding: utf-8 -*-

""" DO! """

# import sys
# sys.path.append("/Users/projects/tmp/do")
from do.params import args
from do.input import read_yamls
from do.builds import find_and_build
from do.utils.logs import get_logger

log = get_logger(__name__)


if __name__ == '__main__':

    # Read necessary files
    services_data = read_yamls(args.get('blueprint'))
    log.pp(services_data)
    print("PAOLO")
    exit(1)
    # Find builds
    find_and_build(services_data)
    # logger
    log.info("done")
