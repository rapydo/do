from typing import Optional

import typer

from controller import log, print_and_exit
from controller.app import Application, Configuration
from controller.deploy.compose import Compose
from controller.deploy.docker import Docker
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
    Application.get_controller().controller_init()

    docker = Docker()
    dc = Compose(files=Application.data.files)

    if not user:
        user = services.get_default_user(service, Configuration.frontend)

    if default_command:
        command = services.get_default_command(service)

    log.debug("Requested command: {} with user: {}", command, user)

    container = docker.get_container(service, slot=1)

    if not container:
        print_and_exit("No running container found for {} service", service)

    # docker.exec_command(container, user=user, command=command, tty=not no_tty)
    dc.exec_command(service, user=user, command=command, disable_tty=no_tty)
