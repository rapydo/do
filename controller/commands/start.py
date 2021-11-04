import time
from typing import List

import typer
from python_on_whales.exceptions import DockerException

from controller import SWARM_MODE, log
from controller.app import Application
from controller.deploy.builds import verify_available_images
from controller.deploy.compose_v2 import Compose as Compose
from controller.deploy.docker import Docker
from controller.deploy.swarm import Swarm


def wait_stack_deploy(swarm: Swarm) -> None:
    MAX = 60
    for i in range(0, MAX):
        try:
            if swarm.get_running_services():
                break

            log.info("Stack is still starting, waiting... [{}/{}]", i + 1, MAX)
            time.sleep(1)
        # Can happens when the stack is near to be deployed
        except DockerException:  # pragma: no cover
            pass


@Application.app.command(help="Start services for this configuration")
# Maybe to be renamed in deploy?
def start(
    services: List[str] = typer.Argument(
        None,
        help="Services to be started",
        shell_complete=Application.autocomplete_service,
    )
) -> None:

    Application.print_command(Application.serialize_parameter("", services))

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
        # if swarm.stack_is_running():
        #     print_and_exit(
        #         "A stack is already running. "
        #         "Stop it with {command1} if you want to start a new stack "
        #         "or use {command2} to update it",
        #         command1=RED("rapydo remove"),
        #         command2=RED("rapydo restart"),
        #     )

        compose.dump_config(Application.data.services)
        swarm.deploy()
        wait_stack_deploy(swarm)

    else:
        # if compose.get_running_services():
        #     print_and_exit(
        #         "A stack is already running. "
        #         "Stop it with {command1} if you want to start a new stack "
        #         "or use {command2} to update it",
        #         command1=RED("rapydo remove"),
        #         command2=RED("rapydo restart"),
        #     )
        compose.start_containers(Application.data.services)

    log.info("Stack started")
