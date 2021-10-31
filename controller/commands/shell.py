from typing import Optional

import typer

from controller import log, print_and_exit
from controller.app import Application
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
    replica: int = typer.Option(
        1,
        "--replica",
        "--slot",
        help="Execute the command on the specified replica",
        show_default=False,
    ),
    broadcast: bool = typer.Option(
        False,
        "--broadcast",
        help="Execute the command on all the replicas",
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

    if replica > 1 and broadcast:
        print_and_exit("--replica and --broadcast options are not compatible")
    Application.get_controller().controller_init()

    docker = Docker()

    if not user:
        user = services.get_default_user(service)

    if default_command:
        command = services.get_default_command(service)

    log.debug("Requested command: {} with user: {}", command, user or "default")
    if broadcast:
        containers = docker.get_containers(service)
        if not containers:
            print_and_exit("No running container found for {} service", service)

        docker.exec_command(containers, user=user, command=command)
    else:
        container = docker.get_container(service, slot=replica)

        if not container:
            if replica != 1:
                print_and_exit(
                    "Replica number {} not found for {} service", str(replica), service
                )
            print_and_exit("No running container found for {} service", service)

        docker.exec_command(container, user=user, command=command)
