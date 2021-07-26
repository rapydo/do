from pathlib import Path
from typing import List

import typer

from controller import COMPOSE_FILE, MULTI_HOST_MODE, log
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
            push=MULTI_HOST_MODE,
            load=True,
            cache=not force,
        )
        log.info("Core images built")

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

    # import socket
    # if MULTI_HOST_MODE and local_registry_images:
    #     log.info("Multi Host Mode is enabled, verifying if the registry is reachable")
    #     # manager.host:port/ => (managaer.host, port)
    #     tokens = registry_host.replace("/", "").split(":")
    #     host = tokens[0]
    #     port = int(tokens[1])
    #     with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
    #         sock.settimeout(1)
    #         try:
    #             result = sock.connect_ex((host, port))
    #         except socket.gaierror:
    #             # The error is not important, let's use a generic -1
    #             # result = errno.ESRCH
    #             result = -1

    #         if result != 0:
    #             print_and_exit(
    #                 "Multi Host Mode is enabled, but registry at {} not reachable",
    #                 registry_host,
    #             )

    docker.client.buildx.bake(
        targets=list(clean_targets),
        files=[COMPOSE_FILE],
        load=True,
        pull=True,
        push=MULTI_HOST_MODE,
        cache=not force,
    )

    log.info("Custom images built")

    return True
