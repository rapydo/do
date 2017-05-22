#!/usr/bin/env python3
# -*- coding: utf-8 -*-

""" DO! """

# import sys
# sys.path.append("/Users/projects/tmp/do")
from do.params import args
from do.builds import find_and_build
from do.utils.logs import get_logger

log = get_logger(__name__)


if __name__ == '__main__':

    # Find builds
    find_and_build(bp=args.get('blueprint'))
    # logger
    log.info("done")
