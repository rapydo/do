"""
Reload services
"""
from typing import List

import typer
from python_on_whales.utils import DockerException

from controller import log, print_and_exit
from controller.app import Application, Configuration
from controller.deploy.docker import Docker


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
    running_services = docker.get_running_services()

    if "frontend" in services and len(services) > 1:
        print_and_exit("Can't reload frontend and other services at once")

    reloaded = 0
    for service in Application.data.services:

        # Special case: frontend in production mode
        if Configuration.production and service == "frontend":
            # Only consider it if explicitly requested in input
            if "frontend" not in services:
                log.debug("Can't reload the frontend if not explicitly requested")
            else:
                log.info("Reloading frontend...")
                # The frontend build stucks in swarm mode... let's start the container
                # always in compose mode when using the reload comand
                Configuration.FORCE_COMPOSE_ENGINE = True
                Application.get_controller().controller_init([service])
                docker = Docker()
                docker.compose.start_containers([service], force=True)
                reloaded += 1
            continue

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

            output = docker.exec_command(
                container,
                user="root",
                command="ls /usr/local/bin/reload",
                force_output_return=True,
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
