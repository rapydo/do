from enum import Enum
from typing import Optional

import typer

from controller import log, print_and_exit
from controller.app import Application, Configuration
from controller.deploy.compose import Compose


class ServiceTypes(str, Enum):

    # New values
    swaggerui = "swaggerui"
    adminer = "adminer"
    flower = "flower"

    # Old values
    swagger = "swagger"
    celery = "celery"
    sqlalchemy = "sqlalchemy"
    mongo = "mongo"


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
) -> bool:
    Application.get_controller().controller_init()

    # Deprecated since 1.2
    if service.value == "celery":
        log.warning("Deprecated interface celery, use flower instead")
        return False

    if service.value == "swagger":
        log.warning("Deprecated interface swagger, use swaggerui instead")
        return False

    if service.value == "sqlalchemy":
        log.warning("Deprecated interface sqlalchemy, use adminer instead")
        return False

    if service.value == "mongo":
        log.warning("Deprecated interface mongo, use adminer instead")
        return False

    service_config = Application.data.compose_config.get(service.value, None)
    if not service_config:  # pragma: no cover
        print_and_exit("Services misconfiguration, can't find {}", service.value)

    try:
        current_ports = service_config.ports.pop(0)
    except IndexError:  # pragma: no cover
        print_and_exit("No default port found?")

    port = port or current_ports.published
    target = current_ports.target

    publish = [f"{port}:{target}"]

    if service.value == "swaggerui":
        if Configuration.production:
            prot = "https"
        else:
            prot = "http"

        log.info(
            "You can access SwaggerUI web page here: {}\n",
            f"{prot}://{Configuration.hostname}:{port}",
        )
    else:
        log.info("Launching interface: {}", service)

    dc = Compose(files=Application.data.files)

    dc.command("pull", {"SERVICE": [service]})

    dc.create_volatile_container(service, publish=publish, detach=detach)

    return True
