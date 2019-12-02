# -*- coding: utf-8 -*-

"""
Parse dockerfiles and check for builds

# https://github.com/DBuildService/dockerfile-parse
# https://docker-py.readthedocs.io/en/stable/
"""
import os
from dockerfile_parse import DockerfileParser
from controller import CONTAINERS_YAML_DIRNAME
from controller import log


name_priorities = [
    'backend',
    'proxy',
    'celery',
    'celeryui',
    'celery-beat',
    'certificates-proxy'
]


def name_priority(name1, name2):
    if name1 not in name_priorities:
        log.warning("Cannot determine build priority name for {}", name1)
        return name2
    if name2 not in name_priorities:
        log.warning("Cannot determine build priority name for {}", name2)
        return name1
    p1 = name_priorities.index(name1)
    p2 = name_priorities.index(name2)
    if p1 <= p2:
        return name1
    return name2


def find_templates_build(base_services):

    templates = {}
    from controller.dockerizing import Dock
    docker = Dock()

    for base_service in base_services:

        template_build = base_service.get('build')

        if template_build is not None:

            template_name = base_service.get('name')
            template_image = base_service.get('image')

            if template_image is None:
                log.exit(
                    "Template builds must have a name, missing for {}".format(
                        template_name)
                )
            else:

                if template_image not in templates:
                    templates[template_image] = {}
                    templates[template_image]['services'] = []
                    templates[template_image]['path'] = template_build.get('context')
                    templates[template_image]['timestamp'] = docker.image_attribute(
                        template_image
                    )

                if 'service' not in templates[template_image]:
                    templates[template_image]['service'] = template_name
                else:
                    templates[template_image]['service'] = name_priority(
                        templates[template_image]['service'],
                        template_name,
                    )
                templates[template_image]['services'].append(template_name)

    return templates


def find_templates_override(services, templates):

    # Template and vanilla builds involved in override
    tbuilds = {}
    vbuilds = {}

    for service in services:

        builder = service.get('build')
        if builder is not None:

            dpath = builder.get('context')
            dockerfile = os.path.join(os.curdir, CONTAINERS_YAML_DIRNAME, dpath)
            dfp = DockerfileParser(dockerfile)

            try:
                cont = dfp.content
                if cont is None:
                    log.warning("Dockerfile is empty?")
                else:
                    log.verbose("Parsed dockerfile {}", dpath)
            except FileNotFoundError as e:
                log.exit(e)

            if dfp.baseimage is None:
                dfp.baseimage = 'unknown_build'
            # elif dfp.baseimage.endswith(':template'):
            elif dfp.baseimage.startswith('rapydo/'):
                if dfp.baseimage not in templates:
                    log.exit(
                        """Unable to find {} in this project
\nPlease inspect the FROM image in {}/Dockerfile
                        """.format(dfp.baseimage, dockerfile)
                    )
                else:
                    vanilla_img = service.get('image')
                    template_img = dfp.baseimage
                    log.verbose("{} overrides {}", vanilla_img, template_img)
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


def remove_redundant_services(services, builds):

    # this will be the output
    non_redundant_services = []

    # Transform: {'build-name': {'services': ['A', 'B'], [...]}
    # Into: {'A': 'build-name', 'B': 'build-name'}
    # NOTE: builds == ALL builds
    flat_builds = {}
    for b in builds:
        for s in builds[b]['services']:
            flat_builds[s] = b

    # Group requested services by builds
    requested_builds = {}
    for service in services:
        build_name = flat_builds.get(service)
        # this service is not built from a rapydo image
        if build_name is None:
            # Let's consider not-rapydo-services as non-redundant
            non_redundant_services.append(service)
            continue

        if build_name not in requested_builds:
            requested_builds[build_name] = []
        requested_builds[build_name].append(service)

    # Transform requested builds from:
    # {'build-name': {'services': ['A', 'B'], [...]}
    # NOTE: only considering requested services
    # to list of non redudant services
    for build in requested_builds:
        redundant_services = requested_builds.get(build)
        if redundant_services is None or len(redundant_services) == 0:
            continue
        if len(redundant_services) == 1:
            non_redundant_services.append(redundant_services[0])
        else:
            service = None
            for serv in redundant_services:

                if service is None:
                    service = serv
                else:
                    service = name_priority(service, serv)
            non_redundant_services.append(service)

    log.verbose(
        "Removed redudant services from {} -> {}", services, non_redundant_services
    )
    return non_redundant_services
