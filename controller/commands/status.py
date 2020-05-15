# -*- coding: utf-8 -*-
from controller.compose import Compose
# from controller import log


def __call__(files, **kwargs):

    dc = Compose(files=files)
    dc.command(
        'ps', {'-q': None, '--services': None, '--quiet': False, '--all': False}
    )
