import typer

from controller.app import Application
from controller.compose import Compose


@Application.app.command(help="Create a single-command container")
def volatile(
    service: str = typer.Argument(..., help="Service name"),
    command: str = typer.Option(
        "bash",
        "--command",
        "-c",
        help="UNIX command to be executed",
        show_default=False,
    ),
    user: str = typer.Option(
        None,
        "--user",
        "-u",
        help="User existing in selected service",
        show_default=False,
    ),
):
    """ One command container (NOT executing on a running one) """
    dc = Compose(files=Application.data.files)
    dc.create_volatile_container(service, command, user=user)
