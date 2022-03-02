"""
Start a single container
"""
import os
from typing import Optional, Tuple

import typer

from controller import REGISTRY, log, print_and_exit
from controller.app import Application, Configuration
from controller.deploy.builds import verify_available_images
from controller.deploy.docker import Docker
from controller.templating import password


def get_publish_port(service: str, port: Optional[int]) -> Tuple[int, int]:
    service_config = Application.data.compose_config.get(service, None)
    if not service_config:
        print_and_exit("Services misconfiguration, can't find {}", service)

    try:
        current_ports = service_config.ports.pop(0)
    except IndexError:  # pragma: no cover
        print_and_exit("No default port found?")

    port = port or current_ports.published
    target = current_ports.target

    return port, target


# This command replaces volatile, interfaces and registry
@Application.app.command(help="Start a single container")
def run(
    service: str = typer.Argument(
        ...,
        help="Service name",
        shell_complete=Application.autocomplete_allservice,
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
    detach: Optional[bool] = typer.Option(
        None,
        "--detach",
        help="Start the container in detach mode (default for non-interfaces)",
        show_default=False,
    ),
) -> None:

    Application.print_command(
        Application.serialize_parameter("--pull", pull, IF=pull),
        Application.serialize_parameter("--debug", debug, IF=debug),
        Application.serialize_parameter("--command", command, IF=command),
        Application.serialize_parameter("--user", user, IF=user),
        Application.serialize_parameter("--port", port, IF=port),
        Application.serialize_parameter("", service),
    )

    Configuration.FORCE_COMPOSE_ENGINE = True

    Application.get_controller().controller_init()

    Application.get_controller().check_placeholders_and_passwords(
        Application.data.compose_config, [service]
    )

    if service == REGISTRY and not Configuration.swarm_mode:
        print_and_exit("Can't start the registry in compose mode")

    docker = Docker()
    if Configuration.swarm_mode:
        if service != REGISTRY:
            docker.registry.ping()
        else:

            if docker.registry.ping(do_exit=False):
                registry = docker.registry.get_host()
                print_and_exit("The registry is already running at {}", registry)

            if docker.client.container.exists("registry"):
                log.debug("The registry container is already existing, removing")
                docker.client.container.remove("registry", force=True)

    if not debug:
        if user:
            print_and_exit("Can't specify a user if debug mode is OFF")
        if command:
            print_and_exit("Can't specify a command if debug mode is OFF")

    if user:
        log.warning(
            "Please remember that users in volatile containers are not mapped on"
            " current uid and gid. You should not write or modify files on volumes"
            " to prevent permissions errors"
        )

    if pull:
        log.info("Pulling image for {}...", service)
        docker.client.compose.pull([service])
    else:
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

        log.info("Starting {}...", service)
        docker.compose.create_volatile_container(
            service,
            command=command,
            user=user,
            # if None the wrapper will automatically switch the default ones
            # How to prevent ports on volatile containers?
            # publish=None,
        )
        log.info("Service {} removed", service)

        return None

    # This is equivalent to the old registry command
    if service == REGISTRY:
        # @ symbol in secrets is not working
        # https://github.com/bitnami/charts/issues/1954
        # Other symbols like # and " also lead to configuration errors
        os.environ["REGISTRY_HTTP_SECRET"] = password(
            param_not_used="",
            length=96
            # , symbols="%*,-.=?[]^_~"
        )

    port, target = get_publish_port(service, port)

    if detach is None:
        if service == "swaggerui" or service == "adminer":
            detach = False
        else:
            detach = True

    log.info("Running {}...", service)

    if service == "swaggerui":
        if Configuration.production:
            prot = "https"
        else:
            prot = "http"

        log.info(
            "You can access SwaggerUI web page here: {}\n",
            f"{prot}://{Configuration.hostname}:{port}",
        )

    if service == "adminer":
        if Configuration.production:
            prot = "https"
        else:
            prot = "http"

        log.info(
            "You can access Adminer interface on: {}\n",
            f"{prot}://{Configuration.hostname}:{port}",
        )

    docker.compose.create_volatile_container(
        service, detach=detach, publish=[(port, target)]
    )
