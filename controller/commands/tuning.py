from enum import Enum

import typer

from controller import log
from controller.app import Application


class Services(str, Enum):
    neo4j = "neo4j"
    postgres = "postgres"


@Application.app.command(help="Tuning suggestion for a service")
def tuning(
    service: Services = typer.Argument(..., help="Service name"),
):
    Application.controller.controller_init()

    service = service.value

    if service == Services.neo4j:

        log.critical("Not implemented yet")

    if service == Services.postgres:

        log.critical("Not implemented yet")
