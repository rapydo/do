from typing import List

import typer

from controller import SWARM_MODE, log, print_and_exit
from controller.app import Application, Configuration
from controller.deploy.builds import verify_available_images
from controller.deploy.compose import Compose
from controller.deploy.compose_v2 import Compose as ComposeV2
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

    if SWARM_MODE:
        swarm = Swarm()
        compose = ComposeV2(Application.data.files)
        if swarm.stack_is_running(Configuration.project):
            print_and_exit(
                "A stack is already running. "
                "Stop it with rapydo remove if you want to start a new stack "
                "or use rapydo restart to update it"
            )

        compose.dump_config(Application.data.services)
        swarm.deploy()
    else:
        dc = Compose(files=Application.data.files)
        dc.start_containers(Application.data.services, force_recreate=False)

    log.info("Stack started")
