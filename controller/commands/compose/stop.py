from typing import List

import typer

from controller import log
from controller.app import Application
from controller.deploy.compose_v2 import Compose


@Application.app.command(help="Stop running containers, but do not remove them")
def stop(
    services: List[str] = typer.Argument(
        None,
        help="Services to be stopped",
        shell_complete=Application.autocomplete_service,
    )
) -> None:
    Application.print_command(Application.serialize_parameter("", services))
    Application.get_controller().controller_init(services)

    dc = Compose(Application.data.files)
    dc.docker.compose.stop(Application.data.services)

    log.info("Stack stopped")
