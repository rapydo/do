import typer

from controller import print_and_exit
from controller.app import Application


# Deprecated since 2.1
@Application.app.command(help="Replaced by run --debug command")
def volatile(
    service: str = typer.Argument(
        ...,
        help="Service name",
        shell_complete=Application.autocomplete_allservice,
    ),
    command: str = typer.Argument(
        "bash", help="UNIX command to be executed on selected running service"
    ),
    user: str = typer.Option(
        None,
        "--user",
        "-u",
        help="User existing in selected service",
        show_default=False,
    ),
) -> None:
    # Deprecated since 2.1
    print_and_exit("Volatile command is replaced by rapydo run --debug {}", service)
