from typing import Optional

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
    command: str = typer.Argument(
        "bash", help="UNIX command to be executed on selected running service"
    ),
    user: Optional[str] = typer.Option(
        None,
        "--user",
        "-u",
        help="User existing in selected service",
        show_default=False,
    ),
    # Deprecated since 0.8
    old_command: str = typer.Option(
        None,
        "--command",
        "-c",
        help="[DEPRECATED] UNIX command to be executed on selected running service",
        show_default=False,
    ),
    default_command: bool = typer.Option(
        False,
        "--default-command",
        "--default",
        help="Execute the default command configured for the container",
        show_default=False,
    ),
    no_tty: bool = typer.Option(
        False,
        "--no-tty",
        help="Disable pseudo-tty allocation (useful for non-interactive script)",
        show_default=False,
    ),
    detach: bool = typer.Option(
        False,
        "--detach",
        help="Execute the command in detach mode",
        show_default=False,
    ),
) -> None:
    Application.get_controller().controller_init()

    # Deprecated since 0.8
    if old_command:
        if " " in old_command:
            cmd = f'"{old_command}"'
        else:
            cmd = old_command
        log.warning(
            "Deprecated use of --command, use: rapydo shell {} {}", service, cmd
        )
        command = old_command

    dc = Compose(files=Application.data.files)

    if not user:
        user = services.get_default_user(service, Configuration.frontend)

    if default_command:
        command = services.get_default_command(service)

    log.debug("Requested command: {} with user: {}", command, user)

    dc.exec_command(
        service, user=user, command=command, disable_tty=no_tty, detach=detach
    )
