from typing import List

import typer
from python_on_whales.utils import DockerException

from controller import SWARM_MODE, log
from controller.app import Application
from controller.deploy.compose_v2 import Compose
from controller.deploy.docker import Docker
from controller.deploy.swarm import Swarm


@Application.app.command(help="Reload services")
def reload(
    services: List[str] = typer.Argument(
        None,
        help="Services to be reloaded",
        shell_complete=Application.autocomplete_service,
    ),
) -> None:

    Application.print_command(Application.serialize_parameter("", services))

    Application.get_controller().controller_init(services)

    docker = Docker()

    if SWARM_MODE:
        swarm = Swarm()
        running_services = swarm.get_running_services()
    else:
        compose = Compose(Application.data.files)
        running_services = compose.get_running_services()

    reloaded = 0
    for service in Application.data.services:

        if service not in running_services:
            continue

        containers = docker.get_containers(service)
        if not containers:
            log.warning("Can't find any container for {}", service)
            continue

        try:
            # get the first container from the containers dict
            container = containers.get(list(containers.keys())[0])

            # Just added for typing purpose
            if not container:  # pragma: no conver
                log.warning("Can't find any container for {}", service)
                continue

            output = docker.client.container.execute(
                container[0],
                user="root",
                command=["ls", "/usr/local/bin/reload"],
                interactive=False,
                tty=False,
                stream=True,
                detach=False,
            )

            # this is to consume the iterator and raise the exception with exit code
            if output:
                [_ for _ in output]

        except DockerException as e:
            # fail2ban fails with code 1
            if "It returned with code 1" in str(e):
                log.warning("Service {} does not support the reload command", service)
                continue

            # backend fails with code 2
            if "It returned with code 2" in str(e):
                log.warning("Service {} does not support the reload command", service)
                continue
            raise

        docker.exec_command(containers, user="root", command="/usr/local/bin/reload")
        reloaded += 1

    if reloaded == 0:
        log.info("No service reloaded")
    else:
        log.info("Services reloaded")
