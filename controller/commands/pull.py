from typing import Set

import typer
from glom import glom

from controller import log
from controller.app import Application
from controller.deploy.docker import Docker


@Application.app.command(help="Pull available images from docker hub")
def pull(
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
    Application.get_controller().controller_init()

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

    docker = Docker()
    docker.client.pull(list(images), quiet=quiet)

    if include_all:
        log.info("Images pulled from docker hub")
    else:
        log.info("Base images pulled from docker hub")
