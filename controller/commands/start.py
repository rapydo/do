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
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Recreate containers even if their configuration/image haven't changed",
        show_default=False,
    ),
) -> None:
    Application.get_controller().controller_init()

    dc = Compose(files=Application.data.files)

    dc.start_containers(Application.data.services, detach=detach, force_recreate=force)

    log.info("Stack started")
