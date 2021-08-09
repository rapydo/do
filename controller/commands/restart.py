from typing import List

import typer

from controller import SWARM_MODE, log, print_and_exit
from controller.app import Application, Configuration
from controller.deploy.compose import Compose
from controller.deploy.swarm import Swarm


@Application.app.command(help="Restart running containers")
def restart(
    services: List[str] = typer.Argument(
        None,
        help="Services to be restarted",
        autocompletion=Application.autocomplete_service,
    ),
) -> None:
    Application.get_controller().controller_init(services)

    if SWARM_MODE:
        swarm = Swarm()
        if not swarm.stack_is_running(Configuration.project):
            print_and_exit(
                "Stack {} is not running, deploy it with rapydo start",
                Configuration.project,
            )

        log.info("Restarting services:")
        for service in Application.data.services:
            swarm.restart(service)
    else:
        dc = Compose(files=Application.data.files)
        dc.start_containers(Application.data.services, force_recreate=True)

    log.info("Stack restarted")
