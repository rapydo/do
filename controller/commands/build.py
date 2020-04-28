# -*- coding: utf-8 -*-
from controller.compose import Compose
from controller import __version__
from controller.utilities import system
from controller.builds import remove_redundant_services
from controller import log


def __call__(args, files, base_files, services, template_builds, builds, **kwargs):

    if args.get('rebuild_templates'):
        dc = Compose(files=base_files)
        log.debug("Forcing rebuild of cached templates")
        dc.build_images(
            template_builds,
            current_version=__version__,
            current_uid=system.get_current_uid(),
            current_gid=system.get_current_gid(),
            no_cache=args.get('force')
        )
        pull_templates = False
    else:
        pull_templates = True

    dc = Compose(files=files)
    services = remove_redundant_services(services, builds)

    options = {
        'SERVICE': services,
        '--no-cache': args.get('force'),
        '--force-rm': True,
        '--pull': pull_templates,
        '--parallel': True,
    }
    dc.command('build', options)

    log.info("Images built")
