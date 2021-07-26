from typing import Dict, Union

import typer
from glom import glom
from python_on_whales import Service

from controller import print_and_exit
from controller.app import Application, Configuration
from controller.deploy.swarm import Swarm

# scaling should be a "Multiple Value"


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
    Application.get_controller().controller_init()

    options = scaling.split("=")
    if len(options) == 2:
        service, nreplicas = options
    else:
        scale_var = f"DEFAULT_SCALE_{scaling.upper()}"
        nreplicas = glom(Configuration.specs, f"variables.env.{scale_var}", default="1")
        service = scaling

    swarm = Swarm()

    service_name = swarm.get_service(service)
    scales: Dict[Union[str, Service], int] = {}
    try:
        scales[service_name] = int(nreplicas)
    except ValueError:
        print_and_exit("Invalid number of replicas: {}", nreplicas)
    swarm.docker.service.scale(scales, detach=not wait)
