# -*- coding: utf-8 -*-
import os
from controller.compose import Compose
from controller import CONFS_DIR
# from controller import log


def __call__(args, **kwargs):

    yml = os.path.join(CONFS_DIR, 'black', 'formatter.yml')

    command = 'run'
    dc = Compose(files=[yml])
    options = dc.command_defaults(command=command)

    VANILLA_SUBMODULE = 'vanilla'
    if args.get('submodule', VANILLA_SUBMODULE) == VANILLA_SUBMODULE:
        options['SERVICE'] = 'vanilla-formatter'
    else:
        options['SERVICE'] = 'submodules-formatter'

    dc.command(command, options)
