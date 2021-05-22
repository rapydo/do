from enum import Enum
from typing import Optional

import typer

from controller import log
from controller.app import Application, Configuration
from controller.compose import Compose


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

    info = container_info(Application.data.services_dict, service.value)
    try:
        current_ports = info.get("ports", []).pop(0)
    except IndexError:  # pragma: no cover
        Application.exit("No default port found?")

    # cannot set current_ports.published as default in get
    # because since port is in args... but can be None
    if port is None:
        port = current_ports.published

    publish = [f"{port}:{current_ports.target}"]

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


def container_info(services_dict, service_name):
    return services_dict.get(service_name, None)
