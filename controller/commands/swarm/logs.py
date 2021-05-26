import typer

from controller import log
from controller.app import Application
from controller.swarm import Swarm


@Application.app.command(help="[SWARM] Watch log tails of all or specified containers")
def logs(
    follow: bool = typer.Option(
        False,
        "--follow",
        "-f",
        help="Follow logs",
        show_default=False,
    ),
    tail: int = typer.Option(
        "500",
        "--tail",
        "-t",
        help="Number of lines to show",
    ),
    nocolor: bool = typer.Option(False, "--no-color", help="Produce monochrome outpu"),
) -> None:
    Application.get_controller().controller_init()

    services = Application.data.services

    if len(services) > 1:
        timestamps = False
    elif services[0] in "frontend":
        timestamps = True
    else:
        timestamps = False

    swarm = Swarm()
    try:
        swarm.logs(services, follow, tail, timestamps)
    except KeyboardInterrupt:
        log.info("Stopped by keyboard")
