"""
Show current services status
"""

import typer

from controller.app import Application
from controller.deploy.docker import Docker


@Application.app.command(help="Show current services status")
def status(
    services: list[str] = typer.Argument(
        None,
        help="Services to be inspected",
        shell_complete=Application.autocomplete_service,
    ),
) -> None:
    Application.print_command(Application.serialize_parameter("", services))

    Application.get_controller().controller_init(services)

    docker = Docker()
    docker.status(Application.data.services)
