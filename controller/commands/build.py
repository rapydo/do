# -*- coding: utf-8 -*-
from controller.compose import Compose
from controller.builds import remove_redundant_services
from controller.builds import locate_builds
from controller import log


def __call__(args, files, base_files, services, base_services,
             compose_config, **kwargs):

    builds, template_builds, overriding_imgs = locate_builds(
        base_services, compose_config
    )

    if args.get('core'):
        log.debug("Forcing rebuild of core builds")

        options = {
            'SERVICE': remove_redundant_services(services, template_builds),
            '--no-cache': args.get('force'),
            '--force-rm': True,
            '--pull': True,
            '--parallel': True,
        }
        dc = Compose(files=base_files)
        dc.command('build', options)

    # Only build images defined at project level, overriding core images
    # Core images should only be pulled or built by specificing --core
    custom_services = []
    for img, build in builds.items():
        if img in overriding_imgs:
            custom_services.extend(build.get('services', []))
    options = {
        'SERVICE': remove_redundant_services(custom_services, builds),
        '--no-cache': args.get('force'),
        '--force-rm': True,
        '--pull': not args.get('core'),
        '--parallel': True,
    }
    dc = Compose(files=files)
    dc.command('build', options)

    log.info("Images built")
