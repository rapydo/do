from typing import List

import typer

from controller import log
from controller.app import Application
from controller.deploy.compose import Compose


@Application.app.command(help="Restart modified running containers")
def restart(
    services: List[str] = typer.Argument(
        None,
        help="Services to be restarted",
        autocompletion=Application.autocomplete_service,
    ),
) -> None:
    Application.get_controller().controller_init(services)

    dc = Compose(files=Application.data.files)
    dc.start_containers(Application.data.services)

    log.info("Stack restarted")
