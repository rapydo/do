import typer

from controller import log
from controller.app import Application
from controller.compose import Compose


@Application.app.command(help="Watch log tails of all or specified containers")
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
    service: str = typer.Option(
        None,
        "--service",
        "-s",
        help="Service name",
        show_default=False,
        autocompletion=Application.autocomplete_service,
    ),
    nocolor: bool = typer.Option(False, "--no-color", help="Produce monochrome outpu"),
) -> None:
    Application.get_controller().controller_init()

    # if provided, use specific service instead of general services opt
    if service:
        services = [service]
    else:
        services = Application.data.services

    if len(services) > 1:
        timestamps = False
    elif services[0] in "frontend":
        timestamps = True
    else:
        timestamps = False

    options = {
        "--follow": follow,
        "--tail": str(tail),
        "--timestamps": timestamps,
        "--no-color": nocolor,
        "SERVICE": services,
    }

    dc = Compose(files=Application.data.files)
    try:
        dc.command("logs", options)
    except KeyboardInterrupt:
        log.info("Stopped by keyboard")
