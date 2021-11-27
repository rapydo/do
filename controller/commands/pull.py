from typing import List, Set

import typer
from glom import glom

from controller import SWARM_MODE, log
from controller.app import Application
from controller.deploy.docker import Docker


@Application.app.command(help="Pull available images from docker hub")
def pull(
    services: List[str] = typer.Argument(
        None,
        help="Services to be pulled",
        shell_complete=Application.autocomplete_service,
    ),
    include_all: bool = typer.Option(
        False,
        "--all",
        help="Include both core and custom images",
        show_default=False,
    ),
    quiet: bool = typer.Option(
        False,
        "--quiet",
        help="Pull without printing progress information",
        show_default=False,
    ),
) -> None:

    Application.print_command(
        Application.serialize_parameter("--all", include_all, IF=include_all),
        Application.serialize_parameter("--quiet", quiet, IF=quiet),
        Application.serialize_parameter("", services),
    )

    Application.get_controller().controller_init(services)

    docker = Docker()

    if SWARM_MODE:
        docker.ping_registry()
        docker.login()

    base_image: str = ""
    image: str = ""
    images: Set[str] = set()

    for service in Application.data.active_services:
        if Application.data.services and service not in Application.data.services:
            continue

        base_image = glom(
            Application.data.base_services, f"{service}.image", default=""
        )

        # from py38 use walrus here
        if base_image:
            images.add(base_image)

        image = glom(Application.data.compose_config, f"{service}.image", default="")

        # include custom services without a bulid to base images
        build = glom(Application.data.compose_config, f"{service}.build", default="")

        if image and (include_all or not build):
            images.add(image)

    docker.client.image.pull(list(images), quiet=quiet)

    if SWARM_MODE:
        registry = docker.get_registry()

        local_images: List[str] = []
        for img in images:
            new_tag = f"{registry}/{img}"
            docker.client.tag(img, new_tag)
            local_images.append(new_tag)
        # push to the local registry
        docker.client.image.push(local_images, quiet=quiet)
        # remove local tags
        docker.client.image.remove(local_images, prune=True)  # type: ignore

    if include_all:
        target = "Images"
    else:
        target = "Base images"

    if SWARM_MODE:
        extra = " and pushed into the local registry"
    else:
        extra = ""

    log.info("{} pulled from docker hub{}", target, extra)
