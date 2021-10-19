from enum import Enum
from typing import Optional

import typer

from controller import log, print_and_exit
from controller.app import Application


class ServiceTypes(str, Enum):

    # New values
    swaggerui = "swaggerui"
    adminer = "adminer"
    flower = "flower"

    # Deprecated since 1.2
    sqlalchemy = "sqlalchemy"


# Deprecated since 2.1
@Application.app.command(help="Execute predefined interfaces to services")
def interfaces(
    service: ServiceTypes = typer.Argument(
        ...,
        help="Service name",
    ),
    detach: bool = typer.Option(
        False,
        "--detach",
        help="Detached mode to run the container in background",
        show_default=False,
    ),
    port: Optional[int] = typer.Option(
        None,
        "--port",
        "-p",
        help="port to be associated to the current service interface",
    ),
) -> None:

    Application.print_command(
        Application.serialize_parameter("--detach", detach, IF=detach),
        Application.serialize_parameter("--port", port, IF=port),
        Application.serialize_parameter("", service),
    )
    # Deprecated since 1.2
    if service.value == "sqlalchemy":
        log.warning("Deprecated interface sqlalchemy, use adminer instead")
        return None

    # Deprecated since 2.1
    print_and_exit("Interfaces command is replaced by rapydo run {}", service)
