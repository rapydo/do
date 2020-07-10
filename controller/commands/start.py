import typer

from controller import log
from controller.app import Application
from controller.compose import Compose


@Application.app.command(help="Start containers for this configuration")
def start(
    detach: bool = typer.Option(
        True,
        "--no-detach",
        help="Disable detach mode and attach to container execution",
        show_default=False,
    ),
):
    Application.controller.controller_init()

    dc = Compose(files=Application.data.files)

    dc.start_containers(Application.data.services, detach=detach)

    log.info("Stack started")
