# -*- coding: utf-8 -*-
from controller.compose import Compose
from controller import log


def __call__(services, files, **kwargs):

    options = {'SERVICE': services}

    dc = Compose(files=files)
    dc.command('stop', options)

    log.info("Stack stopped")
