from typing import List

import typer

from controller import SWARM_MODE, log, print_and_exit
from controller.app import Application, Configuration
from controller.deploy.builds import verify_available_images
from controller.deploy.compose_v2 import Compose as Compose
from controller.deploy.docker import Docker
from controller.deploy.swarm import Swarm


@Application.app.command(help="Start services for this configuration")
def start(
    services: List[str] = typer.Argument(
        None,
        help="Services to be started",
        autocompletion=Application.autocomplete_service,
    )
) -> None:

    Application.get_controller().controller_init(services)

    if SWARM_MODE:
        docker = Docker()
        docker.ping_registry()

    verify_available_images(
        Application.data.services,
        Application.data.compose_config,
        Application.data.base_services,
    )

    compose = Compose(Application.data.files)
    if SWARM_MODE:
        swarm = Swarm()
        if swarm.stack_is_running(Configuration.project):
            print_and_exit(
                "A stack is already running. "
                "Stop it with rapydo remove if you want to start a new stack "
                "or use rapydo restart to update it"
            )

        compose.dump_config(Application.data.services)
        swarm.deploy()
    else:
        if compose.get_running_services(Configuration.project):
            print_and_exit(
                "A stack is already running. "
                "Stop it with rapydo remove if you want to start a new stack "
                "or use rapydo restart to update it"
            )
        compose.start_containers(Application.data.services)

    log.info("Stack started")
