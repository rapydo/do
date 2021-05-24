import typer

from controller import log
from controller.app import Application
from controller.swarm import Swarm


@Application.app.command(help="Start containers for this configuration in Swarm mode")
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

    if detach:
        log.warning("Detach flag is no longer supported")

    if force:
        log.warning("Force flag is not yet implemented")

    swarm = Swarm()
    swarm.deploy()

    log.info("Stack started")
