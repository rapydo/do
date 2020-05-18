# -*- coding: utf-8 -*-
from controller.compose import Compose
from controller.project import ANGULAR
from controller import log


def __call__(args, files, frontend, **kwargs):

    dc = Compose(files=files)
    service = args.get('service')
    no_tty = args.get('no_tty')
    default_command = args.get('default_command')

    user = args.get('user')
    if user is not None and user.strip() == '':
        developer_services = [
            'backend',
            'celery',
            'celeryui',
            'celery-beat'
        ]

        if service in developer_services:
            user = 'developer'
        elif service in ['frontend']:
            if frontend == ANGULAR:
                user = 'node'
        elif service == 'postgres':
            user = 'postgres'
        elif service == 'neo4j':
            user = 'neo4j'
        else:
            # None == get the docker-compose default
            user = None
    log.verbose("Command as user '{}'", user)

    command = args.get('command')
    if command is None:
        if not default_command:
            command = "bash"
        elif service == 'backend':
            command = "restapi launch"
        elif service == 'neo4j':
            command = "bin/cypher-shell"
        else:
            command = "bash"

    return dc.exec_command(service, user=user, command=command, disable_tty=no_tty)
