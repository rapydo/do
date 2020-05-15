# -*- coding: utf-8 -*-
import os
from controller import log


def __call__(project_scaffold, **kwargs):

    for p in project_scaffold.data_folders:
        if not os.path.isdir(p):
            os.makedirs(p)

    for p in project_scaffold.data_files:
        if not os.path.exists(p):
            open(p, 'a').close()

    log.info("Project initialized")
