from typing import Optional

import typer

from controller import log
from controller.app import Application, Configuration
from controller.deploy.swarm import Swarm
from controller.utilities import services


@Application.app.command(help="Open a shell or execute a command onto a container")
def shell(
    service: str = typer.Argument(
        ..., help="Service name", shell_complete=Application.autocomplete_service
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
) -> None:

    Application.print_command(
        Application.serialize_parameter("--user", user, IF=user),
        Application.serialize_parameter(
            "--default", default_command, IF=default_command
        ),
        Application.serialize_parameter("", service),
        Application.serialize_parameter("", command),
    )

    if no_tty:
        log.warning("--no-tty option is deprecated, you can stop using it")

    Application.get_controller().controller_init()

    swarm = Swarm()

    if not user:
        user = services.get_default_user(service, Configuration.frontend)

    if default_command:
        command = services.get_default_command(service)

    log.debug("Requested command: {} with user: {}", command, user)

    swarm.exec_command(service, user=user, command=command)
