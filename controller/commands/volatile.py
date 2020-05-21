# -*- coding: utf-8 -*-
from controller.compose import Compose
# from controller import log


def __call__(args, files, **kwargs):
    """ One command container (NOT executing on a running one) """
    service = args.get('service')
    user = args.get('user')
    command = args.get('command')
    dc = Compose(files=files)
    dc.create_volatile_container(service, command, user=user)
