# -*- coding: utf-8 -*-
from controller.compose import Compose
# from controller import log


def __call__(args, files, **kwargs):
    """ Verify one service connection (inside backend) """
    service = args.get('service')
    dc = Compose(files=files)
    command = 'restapi verify --services {}'.format(service)

    # super magic trick
    try:
        # test the normal container if already running
        return dc.exec_command('backend', command=command, nofailure=True)
    except AttributeError:
        # otherwise shoot a one-time backend container for that
        return dc.create_volatile_container('backend', command)
