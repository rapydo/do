from typing import List

import typer

from controller import log
from controller.app import Application
from controller.deploy.compose import Compose


@Application.app.command(help="Watch log tails of all or specified containers")
def logs(
    services: List[str] = typer.Argument(
        None,
        help="Services to be inspected",
        shell_complete=Application.autocomplete_service,
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
    Application.print_command(
        Application.serialize_parameter("--follow", follow, IF=follow),
        Application.serialize_parameter("--tail", tail, IF=tail),
        Application.serialize_parameter("", services),
    )

    Application.get_controller().controller_init(services)

    services = Application.data.services

    # V2
    # compose = Compose(Application.data.files)
    # try:
    #     compose.logs(services, follow=follow, tail=tail)
    # except KeyboardInterrupt:
    #     log.info("Stopped by keyboard")

    # V1
    if len(services) > 1:
        timestamps = False
        log_prefix = True
    elif services[0] in "frontend":
        timestamps = True
        log_prefix = False
    else:
        timestamps = False
        log_prefix = False

    options = {
        "--follow": follow,
        "--tail": str(tail),
        "--timestamps": timestamps,
        "--no-color": False,
        "--no-log-prefix": not log_prefix,
        "SERVICE": services,
    }

    dc = Compose(files=Application.data.files)

    try:
        dc.command("logs", options)
    except KeyboardInterrupt:
        log.info("Stopped by keyboard")
