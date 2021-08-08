from typing import List

import typer

from controller import log
from controller.app import Application
from controller.deploy.compose import Compose


@Application.app.command(help="Stop running containers, but do not remove them")
def stop(
    services: List[str] = typer.Argument(None, help="Services to be stopped")
) -> None:
    Application.get_controller().controller_init(services)

    options = {"SERVICE": Application.data.services}

    dc = Compose(files=Application.data.files)
    dc.command("stop", options)

    log.info("Stack stopped")
