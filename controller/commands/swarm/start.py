import typer

from controller import log
from controller.app import Application
from controller.deploy.swarm import Swarm


@Application.app.command(help="Start services for this configuration")
def start(
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Recreate containers even if their configuration/image haven't changed",
        show_default=False,
    ),
) -> None:
    Application.get_controller().controller_init()

    if force:
        log.warning("Force flag is not yet implemented")

    swarm = Swarm()
    swarm.deploy()

    log.info("Stack started")
