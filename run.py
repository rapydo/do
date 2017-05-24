#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from do.arguments import current_args
from do.main import Application
from do.utils.logs import get_logger

log = get_logger(__name__)


if __name__ == '__main__':

    # Run the application
    Application(current_args)

    # logger
    log.info("Done")
