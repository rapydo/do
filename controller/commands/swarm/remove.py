from typing import Dict, Union

from python_on_whales import Service

from controller import log
from controller.app import Application, Configuration
from controller.deploy.swarm import Swarm


@Application.app.command(help="Stop and remove services")
def remove() -> None:
    Application.get_controller().controller_init()

    swarm = Swarm()

    all_services = Application.data.services == Application.data.active_services

    if all_services:
        swarm.remove()
        log.info("Stack removed")
    else:

        if not swarm.stack_is_running(Configuration.project):
            Application.exit(
                "Stack {} is not running, deploy it with rapydo start",
                Configuration.project,
            )

        scales: Dict[Union[str, Service], int] = {}
        for service in Application.data.services:
            service_name = swarm.get_service(service)
            scales[service_name] = 0

        swarm.docker.service.scale(scales, detach=False)

        log.info("Services removed")
