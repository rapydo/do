import time
from typing import Dict, List, Union

import typer
from python_on_whales import Service
from python_on_whales.exceptions import DockerException

from controller import RED, REGISTRY, log, print_and_exit
from controller.app import Application, Configuration
from controller.deploy.swarm import Swarm


def wait_network_removal(swarm: Swarm, network: str) -> None:
    for _ in range(0, 60):
        try:
            for n in swarm.docker.network.list():
                if n.driver == "overlay" and n.name == network:
                    break
            else:
                break
            log.debug("{} is still removing, waiting...", network)
            time.sleep(1)
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

    remove_registry = False
    if services and REGISTRY in services:
        # services is a tuple, even if defined as List[str] ...
        services = list(services)
        services.pop(services.index(REGISTRY))
        remove_registry = True

    Application.get_controller().controller_init(services)

    swarm = Swarm()
    if remove_registry:
        swarm.docker.container.remove(REGISTRY, force=True)
        log.info("Registry service removed")

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

        if not swarm.stack_is_running(Configuration.project):
            print_and_exit(
                "Stack {} is not running, deploy it with {command}",
                Configuration.project,
                command=RED("rapydo start"),
            )

        scales: Dict[Union[str, Service], int] = {}
        for service in Application.data.services:
            service_name = swarm.get_service(service)
            scales[service_name] = 0

        swarm.docker.service.scale(scales, detach=False)

        log.info("Services removed")
