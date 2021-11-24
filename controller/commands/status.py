from typing import List

import typer

from controller import SWARM_MODE
from controller.app import Application
from controller.deploy.compose_v2 import Compose
from controller.deploy.swarm import Swarm


@Application.app.command(help="Show current services status")
def status(
    services: List[str] = typer.Argument(
        None,
        help="Services to be inspected",
        shell_complete=Application.autocomplete_service,
    ),
) -> None:

    Application.print_command(Application.serialize_parameter("", services))

    Application.get_controller().controller_init(services)

    if SWARM_MODE:
        swarm = Swarm()
        swarm.status(Application.data.services)
    else:
        compose = Compose(Application.data.files)
        compose.status(Application.data.services)
