"""
Parse dockerfiles and check for builds

# https://github.com/DBuildService/dockerfile-parse
# https://docker-py.readthedocs.io/en/stable/
"""

import sys
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple, cast

from dockerfile_parse import DockerfileParser
from python_on_whales.utils import DockerException

from controller import ComposeConfig, log
from controller.app import Application
from controller.deploy.docker import Docker

name_priorities = [
    "backend",
    "proxy",
    "celery",
    "flower",
    "celery-beat",
    "maintenance",
    "bot",
]


def name_priority(name1: str, name2: str) -> str:
    if name1 not in name_priorities or name2 not in name_priorities:
        log.warning("Cannot determine build priority between {} and {}", name1, name2)
        return name2
    p1 = name_priorities.index(name1)
    p2 = name_priorities.index(name2)
    if p1 <= p2:
        return name1
    return name2


# -> Dict[str, Dict[str, Any]]
# Shoud be a TypedDict istead of Dict[str, Any] with:
#     'services': List[str],
#     'path': str,
#     'timestamp': Optional[str],
#     'service': str

# Build: Dict[str, Dict[str, ]]


def get_image_creation(image_name: str) -> Optional[datetime]:
    try:
        docker = Docker()
        return cast(datetime, docker.client.image.inspect(image_name).created)
    except DockerException:
        return None


def find_templates_build(
    base_services: ComposeConfig, include_image: bool = False
) -> Dict[str, Any]:

    # From python 3.8 could be converted in a TypedDict
    templates = {}

    for template_name, base_service in base_services.items():

        template_build = base_service.get("build")

        if not template_build and not include_image:
            continue

        template_image = base_service.get("image")

        if template_image is None:  # pragma: no cover
            log.critical(
                "Template builds must have a name, missing for {}", template_name
            )
            sys.exit(1)

        if template_image not in templates:
            templates[template_image] = {
                "services": [],
                "path": template_build.get("context") if template_build else None,
                "creation": get_image_creation(template_image),
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


def find_templates_override(
    services: ComposeConfig, templates: Dict[str, Any]
) -> Tuple[Dict[str, Any], Dict[str, str]]:

    # Template and vanilla builds involved in override
    tbuilds: Dict[str, Any] = {}
    vbuilds: Dict[str, str] = {}

    for service in services.values():

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
            log.debug("{} extends {}", vanilla_img, template_img)
            tbuilds[template_img] = templates.get(template_img)
            vbuilds[vanilla_img] = template_img

    return tbuilds, vbuilds


# templates is the return values of a find_templates_build
def get_non_redundant_services(
    templates: Dict[str, Any], targets: List[str]
) -> Set[str]:

    # Removed redundant services
    services_normalization_mapping: Dict[str, str] = {}

    for s in templates.values():
        for s1 in s["services"]:
            s0 = s["service"]
            services_normalization_mapping[s1] = s0

    clean_targets: Set[str] = set()

    for t in targets:
        clean_t = services_normalization_mapping.get(t, t)
        clean_targets.add(clean_t)

    return clean_targets


def verify_available_images(
    services: List[str], compose_config: ComposeConfig, base_services: ComposeConfig
) -> None:

    docker = Docker()
    images: List[str] = []

    for image in docker.client.images():
        images.extend(image.repo_tags)

    # All template builds (core only)
    templates = find_templates_build(base_services, include_image=True)
    clean_core_services = get_non_redundant_services(templates, services)

    for service in clean_core_services:
        for image, data in templates.items():
            if data["service"] != service and service not in data["services"]:
                continue

            if image not in images:
                Application.exit(
                    "Missing {} image for {} service, execute rapydo pull",
                    image,
                    service,
                )

    # All builds used for the current configuration (core + custom)
    builds = find_templates_build(compose_config, include_image=True)
    clean_services = get_non_redundant_services(builds, services)

    for service in clean_services:
        for image, data in builds.items():
            if data["service"] != service and service not in data["services"]:
                continue

            if image not in images:
                action = "build" if data["path"] else "pull"
                Application.exit(
                    "Missing {} image for {} service, execute rapydo {}",
                    image,
                    service,
                    action,
                )
