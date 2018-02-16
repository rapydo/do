# -*- coding: utf-8 -*-

"""
Parse dockerfiles and check for builds

# https://github.com/DBuildService/dockerfile-parse
# https://docker-py.readthedocs.io/en/stable/
"""

from dockerfile_parse import DockerfileParser
from utilities import CONTAINERS_YAML_DIRNAME
from controller.dockerizing import Dock
from utilities import helpers
from utilities.logs import get_logger

log = get_logger(__name__)


def find_templates_build(base_services):

    templates = {}
    docker = Dock()

    for base_service in base_services:

        # log.pp(base_service)
        template_build = base_service.get('build')

        if template_build is not None:

            template_name = base_service.get('name')
            template_image = base_service.get('image')

            if template_image is None:
                log.critical_exit(
                    "Error with template build: %s\n"
                    "Template builds must have a name!"
                    % template_name
                )
            else:
                templates[template_image] = {
                    'service': template_name,
                    'path': template_build.get('context'),
                    'timestamp': docker.image_attribute(template_image)
                }

    return templates


def find_templates_override(services, templates):

    # Template and vanilla builds involved in override
    tbuilds = {}
    vbuilds = {}

    for service in services:

        builder = service.get('build')
        if builder is not None:

            dpath = builder.get('context')
            dockerfile = helpers.current_dir(CONTAINERS_YAML_DIRNAME, dpath)
            dfp = DockerfileParser(dockerfile)

            try:
                cont = dfp.content
                if cont is None:
                    log.warning("Dockerfile is empty?")
                else:
                    log.very_verbose("Parsed dockerfile %s" % dpath)
            except FileNotFoundError as e:
                log.critical_exit(e)

            if dfp.baseimage is None:
                dfp.baseimage = 'unknown_build'
            # elif dfp.baseimage.endswith(':template'):
            elif dfp.baseimage.startswith('rapydo/'):
                if dfp.baseimage not in templates:
                    log.critical_exit(
                        """Unable to find %s in this project
\nPlease inspect the FROM image in %s/Dockerfile
                        """ % (dfp.baseimage, dockerfile)
                    )
                else:
                    vanilla_img = service.get('image')
                    template_img = dfp.baseimage
                    log.verbose("%s overrides %s", vanilla_img, template_img)
                    tbuilds[template_img] = templates.get(template_img)
                    vbuilds[vanilla_img] = template_img

    return tbuilds, vbuilds


def locate_builds(base_services, services):
    # TODO: cool progress bar in cli for the whole function START

    # All builds used for the current configuration (templates + custom)
    builds = find_templates_build(services)

    # All template builds
    templates = find_templates_build(base_services)

    # 2. find templates that were extended in vanilla
    template_imgs, vanilla_imgs = find_templates_override(services, templates)

    # TODO: cool progress bar in cli for the whole function END
    return builds, template_imgs, vanilla_imgs
