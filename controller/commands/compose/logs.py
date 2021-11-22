from typing import List

import typer

from controller import log
from controller.app import Application
from controller.deploy.compose_v2 import Compose


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

    compose = Compose(Application.data.files)
    try:
        compose.logs(services, follow=follow, tail=tail)
    except KeyboardInterrupt:  # pragma: no cover
        log.info("Stopped by keyboard")
