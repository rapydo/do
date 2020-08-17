import typer

from controller import log
from controller.app import Application, Configuration
from controller.compose import Compose
from controller.utilities import services


@Application.app.command(help="Open a shell or execute a command onto a container")
def shell(
    service: str = typer.Argument(
        ..., help="Service name", autocompletion=Application.autocomplete_service
    ),
    user: str = typer.Option(
        None,
        "--user",
        "-u",
        help="User existing in selected service",
        show_default=False,
    ),
    command: str = typer.Option(
        "bash",
        "--command",
        "-c",
        help="UNIX command to be executed on selected running service",
        show_default=False,
    ),
    default_command: bool = typer.Option(
        False,
        "--default-command",
        help="Execute the default command configured for the container. Not compatible with --command and not implemented for all containers",
        show_default=False,
    ),
    no_tty: bool = typer.Option(
        False,
        "--no-tty",
        help="Disable pseudo-tty allocation,"
        "useful to execute the command from non interactive script",
        show_default=False,
    ),
    detach: bool = typer.Option(
        False, "--detach", help="Execute command in detach mode", show_default=False,
    ),
):
    Application.controller.controller_init()

    dc = Compose(files=Application.data.files)

    if not user:
        user = services.get_default_user(service, Configuration.frontend)

    if default_command:
        command = services.get_default_command(service)

    log.debug("Requested command: {} with user: {}", command, user)

    return dc.exec_command(
        service, user=user, command=command, disable_tty=no_tty, detach=detach
    )
