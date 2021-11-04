from typing import List

import typer

from controller import log, print_and_exit
from controller.app import Application
from controller.deploy.swarm import Swarm


@Application.app.command(help="Watch log tails of services")
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
        Application.serialize_parameter("--tail", tail),
        Application.serialize_parameter("", services),
    )
    Application.get_controller().controller_init(services)

    if follow and len(Application.data.services) > 1:
        print_and_exit("Follow flag is not supported on multiple services")

    for service in Application.data.services:
        if service == "frontend":
            timestamps = True
        else:
            timestamps = False

        swarm = Swarm()
        try:
            swarm.logs(service, follow, tail, timestamps)
        except KeyboardInterrupt:  # pragma: no cover
            log.info("Stopped by keyboard")
        print("")
