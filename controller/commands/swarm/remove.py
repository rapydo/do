import time
from typing import Dict, List, Union

import typer
from python_on_whales import Service
from python_on_whales.exceptions import DockerException

from controller import RED, REGISTRY, log, print_and_exit
from controller.app import Application, Configuration
from controller.deploy.docker import Docker
from controller.deploy.swarm import Swarm


def wait_network_removal(swarm: Swarm, network: str) -> None:
    MAX = 30
    for i in range(0, MAX):
        try:
            for n in swarm.docker.network.list():
                if n.driver == "overlay" and n.name == network:
                    break
            else:
                break
            log.info("Stack is still removing, waiting... [{}/{}]", i + 1, MAX)
            time.sleep(2)
        # Can happens when the network is near to be removed and
        # returned by list but no longer available for inspect
        # It is assumed to be removed
        except DockerException:  # pragma: no cover
            break


@Application.app.command(help="Stop and remove services")
def remove(
    services: List[str] = typer.Argument(
        None,
        help="Services to be removed",
        shell_complete=Application.autocomplete_service,
    ),
) -> None:

    Application.print_command(Application.serialize_parameter("", services))

    remove_extras: List[str] = []
    for extra in (
        REGISTRY,
        "adminer",
        "swaggerui",
    ):
        if services and extra in services:
            # services is a tuple, even if defined as List[str] ...
            services = list(services)
            services.pop(services.index(extra))
            remove_extras.append(extra)

    Application.get_controller().controller_init(services)

    swarm = Swarm()
    if remove_extras:
        for extra_service in remove_extras:
            if not swarm.docker.container.exists(extra_service):
                log.error("Service {} is not running", extra_service)
                continue
            swarm.docker.container.remove(extra_service, force=True)
            log.info("Service {} removed", extra_service)

        # Nothing more to do
        if not services:
            return

    all_services = Application.data.services == Application.data.active_services

    if all_services:
        swarm.remove()
        # This is needed because docker stack remove does not support a --wait flag
        # To make the remove command sync and chainable with a start command
        engine = Application.env.get("DEPLOY_ENGINE", "swarm")
        network_name = f"{Configuration.project}_{engine}_default"
        wait_network_removal(swarm, network_name)
        log.info("Stack removed")
    else:

        if not swarm.stack_is_running():
            print_and_exit(
                "Stack {} is not running, deploy it with {command}",
                Configuration.project,
                command=RED("rapydo start"),
            )

        scales: Dict[Union[str, Service], int] = {}
        for service in Application.data.services:
            service_name = Docker.get_service(service)
            scales[service_name] = 0

        swarm.docker.service.scale(scales, detach=False)

        log.info("Services removed")
