import typer

from controller import log
from controller.app import Application
from controller.compose import Compose


@Application.app.command(help="Watch log tails of all or specified containers")
def logs(
    follow: bool = typer.Option(
        False, "--follow", "-f", help="Follow logs", show_default=False,
    ),
    tail: int = typer.Option("500", "--tail", "-t", help="Number of lines to show",),
    service: str = typer.Option(
        None,
        "--service",
        "-s",
        help="Service name",
        show_default=False,
        autocompletion=Application.autocomplete_service,
    ),
):
    Application.controller.controller_init()

    # if provided, use specific service instead of general services opt
    if service:
        services = [service]
    else:
        services = Application.data.services

    options = {
        "--follow": follow,
        "--tail": str(tail),
        "--no-color": False,
        "--timestamps": True,
        "SERVICE": services,
    }

    dc = Compose(files=Application.data.files)
    try:
        dc.command("logs", options)
    except KeyboardInterrupt:
        log.info("Stopped by keyboard")
