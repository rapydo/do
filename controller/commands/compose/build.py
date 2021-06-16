from typing import List

import typer

from controller import COMPOSE_FILE, MULTI_HOST_MODE, log
from controller.app import Application, Configuration
from controller.builds import find_templates_build, find_templates_override
from controller.compose import Compose
from controller.deploy.docker import Docker


@Application.app.command(help="Force building of one or more services docker images")
def build(
    core: bool = typer.Option(
        False,
        "--core",
        help="force the build of all images including core builds",
        show_default=False,
    ),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="remove the cache to force a rebuilding",
        show_default=False,
    ),
) -> bool:
    Application.get_controller().controller_init()

    enabled_services: List[str] = []
    for service in Application.data.active_services:
        if Configuration.services_list and service not in Configuration.services_list:
            continue

        enabled_services.append(service)

    docker = Docker()
    if core:
        log.debug("Forcing rebuild of core builds")
        # Create merged compose file with only core files
        dc = Compose(files=Application.data.base_files)
        compose_config = dc.config(relative_paths=True)
        dc.dump_config(compose_config, COMPOSE_FILE, Application.data.active_services)
        log.debug("Compose configuration dumped on {}", COMPOSE_FILE)

        docker.client.buildx.bake(
            targets=enabled_services,
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

    templates = find_templates_build(Application.data.base_services)
    template_builds, _ = find_templates_override(
        Application.data.compose_config, templates
    )

    services_with_custom_builds: List[str] = []
    for b in template_builds.values():
        services_with_custom_builds.extend(b["services"])

    targets: List[str] = []
    for service in Application.data.active_services:
        if Configuration.services_list and service not in Configuration.services_list:
            continue

        if service in services_with_custom_builds:
            targets.append(service)

    if not targets:
        log.info("No custom images to build")
        return False

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
    #             Application.exit(
    #                 "Multi Host Mode is enabled, but registry at {} not reachable",
    #                 registry_host,
    #             )

    docker.client.buildx.bake(
        targets=targets,
        files=[COMPOSE_FILE],
        load=True,
        pull=True,
        push=MULTI_HOST_MODE,
        cache=not force,
    )

    log.info("Custom images built")

    return True
