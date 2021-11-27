from typing import Dict, Union

import typer
from glom import glom
from python_on_whales import Service
from python_on_whales.exceptions import NoSuchService

from controller import print_and_exit
from controller.app import Application, Configuration
from controller.deploy.builds import verify_available_images
from controller.deploy.docker import Docker
from controller.deploy.swarm import Swarm

# RabbitMQ:
# https://www.erlang-solutions.com/blog/scaling-rabbitmq-on-a-coreos-cluster-through-docker/
supported_services = [
    "adminer",
    "backend",
    "celery",
    "flower",
    "ftp",
    # To allow nginx to access the real client IP it is now deployed in global mode
    # to be able to map the port directly on the host, instead of being load balanced
    # In this way the proxy can no longer be scaled
    # "proxy",
    "swaggerui",
]


@Application.app.command(help="Scale the number of replicas for a service")
def scale(
    scaling: str = typer.Argument(..., help="scale SERVICE to NUM_REPLICA"),
    wait: bool = typer.Option(
        False,
        "--wait",
        help="Wait service convergence",
        show_default=False,
    ),
) -> None:
    Application.print_command(
        Application.serialize_parameter("--wait", wait, IF=wait),
        Application.serialize_parameter("", scaling),
    )
    Application.get_controller().controller_init()

    options = scaling.split("=")
    if len(options) == 2:
        service, nreplicas = options
    else:
        scale_var = f"DEFAULT_SCALE_{scaling.upper()}"
        nreplicas = glom(Configuration.specs, f"variables.env.{scale_var}", default="1")
        service = scaling

    docker = Docker()

    service_name = docker.get_service(service)
    scales: Dict[Union[str, Service], int] = {}
    try:
        scales[service_name] = int(nreplicas)
    except ValueError:
        print_and_exit("Invalid number of replicas: {}", nreplicas)

    # Stop core services non compatible with scale with 2+ instances
    if scales[service_name] >= 2:
        core_services = list(Application.data.base_services.keys())
        if service in core_services and service not in supported_services:
            print_and_exit(
                "Service {} is not guaranteed to support the scale, "
                "can't accept the request",
                service,
            )

    docker.ping_registry()

    verify_available_images(
        [service],
        Application.data.compose_config,
        Application.data.base_services,
    )

    swarm = Swarm()
    try:
        swarm.docker.service.scale(scales, detach=not wait)
    # Can happens in case of scale before start
    except NoSuchService:
        print_and_exit(
            "No such service: {}, have you started your stack?", service_name
        )
