"""
Parse dockerfiles and check for builds

# https://github.com/DBuildService/dockerfile-parse
# https://docker-py.readthedocs.io/en/stable/
"""

from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set, Union, cast

from python_on_whales.exceptions import NoSuchImage

from controller import RED, SWARM_MODE, ComposeServices, log, print_and_exit
from controller.deploy.docker import Docker

name_priorities = [
    "backend",
    "proxy",
    "celery",
    "flower",
    "celerybeat",
    "maintenance",
    "bot",
]

# From python 3.8 could be converted in a TypedDict
# service -> str
# services -> List[str]
# path -> Optional[Path]
BuildInfo = Dict[str, Dict[str, Union[str, List[str], Optional[Path]]]]


def name_priority(name1: str, name2: str) -> str:
    if name1 not in name_priorities or name2 not in name_priorities:
        log.warning("Cannot determine build priority between {} and {}", name1, name2)
        return name2
    p1 = name_priorities.index(name1)
    p2 = name_priorities.index(name2)
    if p1 <= p2:
        return name1
    return name2


def get_image_creation(image_name: str) -> datetime:
    docker = Docker()
    try:
        return docker.client.image.inspect(image_name).created
    except NoSuchImage:
        return datetime.fromtimestamp(0)


def find_templates_build(
    base_services: ComposeServices, include_image: bool = False
) -> BuildInfo:

    templates: BuildInfo = {}

    for template_name, base_service in base_services.items():

        template_build = base_service.build

        if not template_build and not include_image:
            continue

        template_image = base_service.image

        if template_image is None:  # pragma: no cover
            print_and_exit(
                "Template builds must have a name, missing for {}", template_name
            )
        if template_image not in templates:
            templates[template_image] = {
                "services": [],
                "path": template_build.context if template_build else None,
            }
        if "service" not in templates[template_image]:
            templates[template_image]["service"] = template_name
        else:
            templates[template_image]["service"] = name_priority(
                # from py38 a typed dict will replace this cast
                cast(str, templates[template_image]["service"]),
                template_name,
            )
        # from py38 a typed dict will replace this cast
        cast(List[str], templates[template_image]["services"]).append(template_name)

    return templates


def get_dockerfile_base_image(path: Path, templates: BuildInfo) -> str:

    dockerfile = path.joinpath("Dockerfile")

    if not dockerfile.exists():
        print_and_exit("Build path not found: {}", dockerfile)

    with open(dockerfile) as f:
        for line in reversed(f.readlines()):
            line = line.strip().lower()
            if line.startswith("from "):
                # from python 3.9 it will be:
                # image = line.removeprefix("from ")
                image = line[5:]
                if " as " in image:
                    image = image.split(" as ")[0]

                if image.startswith("rapydo/") and image not in templates:
                    print_and_exit(
                        "Unable to find {} in this project"
                        "\nPlease inspect the FROM image in {}/Dockerfile",
                        image,
                        dockerfile,
                    )

                return image

    print_and_exit("Invalid Dockerfile, no base image found in {}", dockerfile)


def find_templates_override(
    services: ComposeServices, templates: BuildInfo
) -> Dict[str, str]:

    builds: Dict[str, str] = {}

    for service in services.values():

        if service.build is not None and service.image not in templates:

            baseimage = get_dockerfile_base_image(service.build.context, templates)

            if not baseimage.startswith("rapydo/"):
                continue

            vanilla_img = service.image
            template_img = baseimage
            log.debug("{} extends {}", vanilla_img, template_img)
            builds[vanilla_img] = template_img

    return builds


def get_non_redundant_services(templates: BuildInfo, targets: List[str]) -> Set[str]:

    # Removed redundant services
    services_normalization_mapping: Dict[str, str] = {}

    for s in templates.values():
        # from py38 a typed dict will replace this cast
        for s1 in cast(List[str], s["services"]):
            # from py38 a typed dict will replace this cast
            s0 = cast(str, s["service"])
            services_normalization_mapping[s1] = s0

    clean_targets: Set[str] = set()

    for t in targets:
        clean_t = services_normalization_mapping.get(t, t)
        clean_targets.add(clean_t)

    return clean_targets


def verify_available_images(
    services: List[str],
    compose_config: ComposeServices,
    base_services: ComposeServices,
    is_run_command: bool = False,
) -> None:

    docker = Docker()
    # All template builds (core only)
    templates = find_templates_build(base_services, include_image=True)
    clean_core_services = get_non_redundant_services(templates, services)

    for service in sorted(clean_core_services):
        for image, data in templates.items():
            # from py38 a typed dict will replace this cast
            data_services = cast(List[str], data["services"])
            if data["service"] != service and service not in data_services:
                continue

            if SWARM_MODE and not is_run_command:
                image_exists = docker.verify_registry_image(image)
            else:
                image_exists = docker.client.image.exists(image)

            if not image_exists:
                if is_run_command:
                    print_and_exit(
                        "Missing {} image, add {opt} option", image, opt=RED("--pull")
                    )
                else:
                    print_and_exit(
                        "Missing {} image, execute {command}",
                        image,
                        command=RED(f"rapydo pull {service}"),
                    )

    # All builds used for the current configuration (core + custom)
    builds = find_templates_build(compose_config, include_image=True)
    clean_services = get_non_redundant_services(builds, services)

    for service in clean_services:
        for image, data in builds.items():
            # from py38 a typed dict will replace this cast
            data_services = cast(List[str], data["services"])
            if data["service"] != service and service not in data_services:
                continue

            if SWARM_MODE and not is_run_command:
                image_exists = docker.verify_registry_image(image)
            else:
                image_exists = docker.client.image.exists(image)
            if not image_exists:
                action = "build" if data["path"] else "pull"
                print_and_exit(
                    "Missing {} image, execute {command}",
                    image,
                    command=RED(f"rapydo {action} {service}"),
                )
