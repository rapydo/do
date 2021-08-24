from typing import List

import typer

from controller import log
from controller.app import Application
from controller.deploy.compose import Compose


@Application.app.command(help="Restart modified running containers")
def restart() -> None:
    Application.get_controller().controller_init()

    dc = Compose(files=Application.data.files)
    dc.start_containers(Application.data.services)

    log.info("Stack restarted")
