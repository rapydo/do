import typer

from controller.app import Application
from controller.compose import Compose


@Application.app.command(help="Test if service is reachable from the backend")
def verify(
    service: str = typer.Argument(
        ..., help="Service name", autocompletion=Application.autocomplete_service
    ),
    no_tty: bool = typer.Option(
        False,
        "--no-tty",
        help="Disable pseudo-tty allocation (useful for non-interactive script)",
        show_default=False,
    ),
) -> None:
    Application.get_controller().controller_init()

    # Verify one service connection (inside backend)
    dc = Compose(files=Application.data.files)
    command = f"restapi verify --services {service}"

    try:
        dc.exec_command("backend", command=command, disable_tty=no_tty)
    except SystemExit:
        pass
