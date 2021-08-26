import os
from typing import List, Optional

import typer

from controller import SWARM_MODE, log, print_and_exit
from controller.app import Application, Configuration
from controller.deploy.builds import verify_available_images
from controller.deploy.compose import Compose
from controller.deploy.docker import Docker
from controller.templating import password

interfaces = ["swaggerui", "adminer", "flower"]


def get_publish_port(service: str, port: Optional[int]) -> List[str]:
    service_config = Application.data.compose_config.get(service, None)
    if not service_config:  # pragma: no cover
        print_and_exit("Services misconfiguration, can't find {}", service)

    try:
        current_ports = service_config.ports.pop(0)
    except IndexError:  # pragma: no cover
        print_and_exit("No default port found?")

    port = port or current_ports.published
    target = current_ports.target

    publish = [f"{port}:{target}"]

    return publish


# This command replaces volatile, interfaces and registry
@Application.app.command(help="Start a single container")
def run(
    service: str = typer.Argument(
        ...,
        help="Service name",
        autocompletion=Application.autocomplete_allservice,
    ),
    pull: bool = typer.Option(
        False,
        "--pull",
        help="Pull the image before starting the container",
        show_default=False,
    ),
    debug: bool = typer.Option(
        False,
        "--debug",
        help="Start the container in debug mode",
        show_default=False,
    ),
    command: str = typer.Option(
        None,
        "--command",
        help="UNIX command to be executed in the container",
        show_default=False,
    ),
    user: str = typer.Option(
        None,
        "--user",
        "-u",
        help="User existing in selected service",
        show_default=False,
    ),
    port: Optional[int] = typer.Option(
        None,
        "--port",
        "-p",
        help="port to be associated to the current service interface",
    ),
) -> None:

    Configuration.FORCE_COMPOSE_ENGINE = True

    Application.get_controller().controller_init()

    Application.get_controller().check_placeholders(
        Application.data.compose_config, [service]
    )

    if SWARM_MODE:
        docker = Docker()
        if service != "registry":
            docker.ping_registry()
        elif docker.ping_registry(do_exit=False):
            registry = docker.get_registry()
            print_and_exit("The registry is already running at {}", registry)

    if not debug:
        if user:
            print_and_exit("Can't specify a user if debug mode is OFF")
        if command:
            print_and_exit("Can't specify a command if debug mode is OFF")

    if user:
        log.warning(
            "Please remember that users in volatile containers are not mapped "
            "on current uid and gid. "
            "You should avoid to write or modify files on volumes"
        )

    compose = Compose(files=Application.data.files)

    if pull:
        compose.command("pull", {"SERVICE": [service]})
    elif service != "registry":
        verify_available_images(
            [service],
            Application.data.compose_config,
            Application.data.base_services,
            is_run_command=True,
        )

    # This is equivalent to the old volatile command
    if debug:
        if not command:
            command = "bash"

        compose.create_volatile_container(
            service,
            command=command,
            user=user,
            # if None the wrapper will automatically switch the default ones
            # How to prevent ports on volatile containers?
            # publish=None,
        )

        return None

    # This is equivalent to the old registry command
    if service == "registry":
        # @ symbol in secrets is not working
        # https://github.com/bitnami/charts/issues/1954
        # Other symbols like # and " also lead to configuration errors
        os.environ["REGISTRY_HTTP_SECRET"] = password(
            param_not_used="",
            length=96
            # , symbols="%*,-.=?[]^_~"
        )

    publish = get_publish_port(service, port)

    compose.create_volatile_container(service, detach=True, publish=publish)
