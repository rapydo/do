# -*- coding: utf-8 -*-
from controller.compose import Compose
from controller import log


def __call__(args, services, files, **kwargs):

    dc = Compose(files=files)

    rm_all = args.get('all', False)
    rm_networks = args.get('networks', False)

    if rm_networks or rm_all:

        services_specified = args.get('services')
        if services_specified is not None:

            opt = "--networks" if rm_networks else "--all"

            log.exit(
                "Incompatibile options {opt} and --services\n" +
                "rapydo remove {opt} is ALWAYS applied to EVERY container of the " +
                "stack due to the underlying docker-compose implementation. " +
                "If you want to continue remove --services option", opt=opt
            )
        else:

            options = {
                '--volumes': rm_all,
                '--remove-orphans': False,
                '--rmi': 'local',  # 'all'
            }
            dc.command('down', options)
    else:

        options = {
            'SERVICE': services,
            # '--stop': True,  # BUG? not working
            '--force': True,
            '-v': False,  # dangerous?
        }
        dc.command('stop', options)
        dc.command('rm', options)

    log.info("Stack removed")
