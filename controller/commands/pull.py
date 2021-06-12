from typing import Set

import typer
from glom import glom
from python_on_whales import docker

from controller import log
from controller.app import Application, Configuration


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

    if Configuration.services_list:
        for s in Application.data.services:
            if s not in Application.data.base_services.keys():
                Application.exit("Invalid service name: {}", s)

    base_image: str = ""
    image: str = ""
    images: Set[str] = set()
    for service in Application.data.active_services:
        if Configuration.services_list and service not in Configuration.services_list:
            continue
        base_image = glom(
            Application.data.base_services, f"{service}.image", default=""
        )

        # from py38 use walrus here
        if base_image:
            images.add(base_image)

        if include_all:
            image = glom(
                Application.data.compose_config, f"{service}.image", default=""
            )
            # from py38 use walrus here
            if image:
                images.add(image)

    docker.pull(list(images), quiet=quiet)

    if include_all:
        log.info("Images pulled from docker hub")
    else:
        log.info("Base images pulled from docker hub")
