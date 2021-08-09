import typer

from controller import log
from controller.app import Application
from controller.deploy.swarm import Swarm


@Application.app.command(help="Watch log tails of services")
def logs(
    service: str = typer.Argument(
        ...,
        help="Service to be inspected",
        autocompletion=Application.autocomplete_service,
    ),
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
) -> None:
    Application.get_controller().controller_init()

    if service == "frontend":
        timestamps = True
    else:
        timestamps = False

    swarm = Swarm()
    try:
        swarm.logs(service, follow, tail, timestamps)
    except KeyboardInterrupt:  # pragma: no cover
        log.info("Stopped by keyboard")
