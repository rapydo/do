import time
from typing import Dict, List, Union

import typer
from python_on_whales import Service

from controller import log, print_and_exit
from controller.app import Application, Configuration
from controller.deploy.swarm import Swarm


@Application.app.command(help="Stop and remove services")
def remove(
    services: List[str] = typer.Argument(
        None,
        help="Services to be removed",
        autocompletion=Application.autocomplete_service,
    ),
) -> None:
    Application.get_controller().controller_init(services)

    swarm = Swarm()

    all_services = Application.data.services == Application.data.active_services

    if all_services:
        swarm.remove()
        # This sleep is added to add a delay before completing the command
        # This way even if swarm remove is asynchronous, the command can be
        # chained with a start command without raising errors
        time.sleep(1)
        log.info("Stack removed")
    else:

        if not swarm.stack_is_running(Configuration.project):
            print_and_exit(
                "Stack {} is not running, deploy it with rapydo start",
                Configuration.project,
            )

        scales: Dict[Union[str, Service], int] = {}
        for service in Application.data.services:
            service_name = swarm.get_service(service)
            scales[service_name] = 0

        swarm.docker.service.scale(scales, detach=False)

        log.info("Services removed")
