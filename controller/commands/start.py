"""
Start services for the current configuration
"""
import time
from typing import List

import typer
from python_on_whales.exceptions import DockerException

from controller import log
from controller.app import Application, Configuration
from controller.deploy.builds import verify_available_images
from controller.deploy.docker import Docker


def wait_stack_deploy(docker: Docker) -> None:
    MAX = 60
    for i in range(0, MAX):
        try:
            if docker.get_running_services():
                break

            log.info("Stack is still starting, waiting... [{}/{}]", i + 1, MAX)
            time.sleep(1)
        # Can happens when the stack is near to be deployed
        except DockerException:  # pragma: no cover
            pass


@Application.app.command(help="Start services for the current configuration")
# Maybe to be renamed in deploy?
def start(
    services: List[str] = typer.Argument(
        None,
        help="Services to be started",
        shell_complete=Application.autocomplete_service,
    ),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Force containers restart",
        show_default=False,
    ),
) -> None:

    Application.print_command(Application.serialize_parameter("", services))

    Application.get_controller().controller_init(services)

    docker = Docker()
    if Configuration.swarm_mode:
        docker.registry.ping()

    verify_available_images(
        Application.data.services,
        Application.data.compose_config,
        Application.data.base_services,
    )

    if Configuration.swarm_mode:
        docker.compose.dump_config(Application.data.services)
        docker.swarm.deploy()

        if force:
            for service in Application.data.services:
                docker.client.service.update(
                    f"{Configuration.project}_{service}", detach=True, force=True
                )
        wait_stack_deploy(docker)
    else:
        docker.compose.start_containers(Application.data.services, force=force)

    log.info("Stack started")
