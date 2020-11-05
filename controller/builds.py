"""
Parse dockerfiles and check for builds

# https://github.com/DBuildService/dockerfile-parse
# https://docker-py.readthedocs.io/en/stable/
"""

import sys
from typing import Dict, List

from dockerfile_parse import DockerfileParser

from controller import log

name_priorities = [
    "backend",
    "proxy",
    "celery",
    "celeryui",
    "celery-beat",
    "maintenance",
    "bot",
]


def name_priority(name1, name2):
    if name1 not in name_priorities or name2 not in name_priorities:
        log.warning("Cannot determine build priority between {} and {}", name1, name2)
        return name2
    p1 = name_priorities.index(name1)
    p2 = name_priorities.index(name2)
    if p1 <= p2:
        return name1
    return name2


def find_templates_build(base_services):

    # From python 3.8 could be converted in a TypedDict
    templates = {}
    from controller.dockerizing import Dock

    docker = Dock()

    for base_service in base_services:

        template_build = base_service.get("build")

        if template_build is not None:

            template_name = base_service.get("name")
            template_image = base_service.get("image")

            if template_image is None:  # pragma: no cover
                log.critical(
                    "Template builds must have a name, missing for {}".format(
                        template_name
                    )
                )
                sys.exit(1)

            if template_image not in templates:
                templates[template_image] = {
                    "services": [],
                    "path": template_build.get("context"),
                    "timestamp": docker.image_attribute(template_image),
                }

            if "service" not in templates[template_image]:
                templates[template_image]["service"] = template_name
            else:
                templates[template_image]["service"] = name_priority(
                    templates[template_image]["service"],
                    template_name,
                )
            templates[template_image]["services"].append(template_name)

    return templates


def find_templates_override(services, templates):

    # Template and vanilla builds involved in override
    tbuilds = {}
    vbuilds = {}

    for service in services:

        builder = service.get("build")
        if builder is not None:

            dfp = DockerfileParser(builder.get("context"))

            try:
                cont = dfp.content
                if not cont:
                    log.critical(
                        "Build failed, is {}/Dockerfile empty?", builder.get("context")
                    )
                    sys.exit(1)
            except FileNotFoundError as e:
                log.critical(e)
                sys.exit(1)

            if dfp.baseimage is None:
                log.critical(
                    "No base image found in {}/Dockerfile, unable to build",
                    builder.get("context"),
                )
                sys.exit(1)

            if not dfp.baseimage.startswith("rapydo/"):
                continue

            if dfp.baseimage not in templates:
                log.critical(
                    "Unable to find {} in this project"
                    "\nPlease inspect the FROM image in {}/Dockerfile",
                    dfp.baseimage,
                    builder.get("context"),
                )
                sys.exit(1)

            vanilla_img = service.get("image")
            template_img = dfp.baseimage
            log.debug("{} overrides {}", vanilla_img, template_img)
            tbuilds[template_img] = templates.get(template_img)
            vbuilds[vanilla_img] = template_img

    return tbuilds, vbuilds


def locate_builds(base_services, services):

    # All builds used for the current configuration (templates + custom)
    builds = find_templates_build(services)

    # All template builds
    templates = find_templates_build(base_services)

    # 2. find templates that were extended in vanilla
    template_imgs, vanilla_imgs = find_templates_override(services, templates)

    # TODO: cool progress bar in cli for the whole function END
    return builds, template_imgs, vanilla_imgs


def remove_redundant_services(services, builds):

    # Sort the list of services to obtain determinist outputs
    services.sort()
    # this will be the output
    non_redundant_services = []

    # Transform: {'build-name': {'services': ['A', 'B'], [...]}
    # Into: {'A': 'build-name', 'B': 'build-name'}
    # NOTE: builds == ALL builds
    flat_builds = {}
    for b in builds:
        for s in builds[b]["services"]:
            flat_builds[s] = b

    # Group requested services by builds
    requested_builds: Dict[str, List[str]] = {}
    for service in services:
        build_name = flat_builds.get(service)
        # this service is not built from a rapydo image
        if build_name is None:
            # Let's consider not-rapydo-services as non-redundant
            non_redundant_services.append(service)
            continue

        requested_builds.setdefault(build_name, [])
        requested_builds[build_name].append(service)

    # Transform requested builds from:
    # {'build-name': {'services': ['A', 'B'], [...]}
    # NOTE: only considering requested services
    # to list of non redundant services
    for build in requested_builds:
        redundant_services = requested_builds.get(build)
        if not redundant_services:  # pragma: no cover
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

    if len(services) != len(non_redundant_services):
        log.info(
            "Removed redundant builds from {} -> {}", services, non_redundant_services
        )
    return non_redundant_services
