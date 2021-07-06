from typing import Dict

import typer
from glom import glom
from python_on_whales.components.service.cli_wrapper import ValidService

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
    if len(options) != 2:
        scale_var = f"DEFAULT_SCALE_{scaling.upper()}"
        nreplicas = glom(
            Configuration.specs, f"variables.env.{scale_var}", default=None
        )
        if nreplicas is None:
            hints = f"You can also set a {scale_var} variable in your .projectrc file"

            Application.exit(
                "Please specify how to scale: SERVICE=NUM_REPLICA\n\n{}", hints
            )
        service = scaling
    else:
        service, nreplicas = options

    if isinstance(nreplicas, str) and not nreplicas.isnumeric():
        Application.exit("Invalid number of replicas: {}", nreplicas)

    if nreplicas is not None:
        swarm = Swarm()

        service_name = swarm.get_service(service)
        scales: Dict[ValidService, int] = {service_name: nreplicas}
        swarm.docker.service.scale(scales, detach=not wait)

    else:  # pragma: no cover
        Application.exit("Number of replica is missing")
