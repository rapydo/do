from pathlib import Path
from typing import List, Set

import typer

from controller import COMPOSE_FILE, SWARM_MODE, log
from controller.app import Application
from controller.deploy.builds import (
    find_templates_build,
    get_dockerfile_base_image,
    get_non_redundant_services,
)
from controller.deploy.compose import Compose
from controller.deploy.docker import Docker


@Application.app.command(help="Force building of one or more services docker images")
def build(
    core: bool = typer.Option(
        False,
        "--core",
        help="Include core images to the build list",
        show_default=False,
    ),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="remove the cache to force the build",
        show_default=False,
    ),
) -> bool:
    Application.get_controller().controller_init()

    docker = Docker()

    if SWARM_MODE:
        docker.ping_registry()
        docker.login()

    images: Set[str] = set()
    if core:
        log.debug("Forcing rebuild of core builds")
        # Create merged compose file with only core files
        dc = Compose(files=Application.data.base_files)
        compose_config = dc.config(relative_paths=True)
        dc.dump_config(compose_config, COMPOSE_FILE, Application.data.active_services)
        log.debug("Compose configuration dumped on {}", COMPOSE_FILE)

        docker.client.buildx.bake(
            targets=Application.data.services,
            files=[COMPOSE_FILE],
            pull=True,
            load=True,
            cache=not force,
        )
        log.info("Core images built")
        if SWARM_MODE:
            log.warning("Local registry push is not implemented yet for core images")

    dc = Compose(files=Application.data.files)
    compose_config = dc.config(relative_paths=True)
    dc.dump_config(compose_config, COMPOSE_FILE, Application.data.active_services)
    log.debug("Compose configuration dumped on {}", COMPOSE_FILE)

    core_builds = find_templates_build(Application.data.base_services)
    all_builds = find_templates_build(Application.data.compose_config)

    services_with_custom_builds: List[str] = []
    for image, build in all_builds.items():
        if image not in core_builds:

            # this is used to validate the taregt Dockerfile:
            get_dockerfile_base_image(Path(build.get("path")), core_builds)
            services_with_custom_builds.extend(build["services"])
            images.add(image)

    targets: List[str] = []
    for service in Application.data.active_services:
        if Application.data.services and service not in Application.data.services:
            continue

        if service in services_with_custom_builds:
            targets.append(service)

    if not targets:
        log.info("No custom images to build")
        return False

    clean_targets = get_non_redundant_services(all_builds, targets)

    docker.client.buildx.bake(
        targets=list(clean_targets),
        files=[COMPOSE_FILE],
        load=True,
        pull=True,
        cache=not force,
    )

    if SWARM_MODE:
        registry = docker.get_registry()

        local_images: List[str] = []
        for img in images:
            new_tag = f"{registry}/{img}"
            docker.client.tag(img, new_tag)
            local_images.append(new_tag)

        # push to the local registry
        docker.client.image.push(local_images, quiet=False)
        # remove local tags
        docker.client.image.remove(local_images, prune=True)  # type: ignore

        log.info("Custom images built and pushed into the local registry")
    else:
        log.info("Custom images built")

    return True
