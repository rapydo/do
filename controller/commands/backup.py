from enum import Enum

import typer

from controller import log
from controller.app import Application


class Services(str, Enum):
    neo4j = "neo4j"
    postgres = "postgres"


@Application.app.command(help="Execute a backup of one service")
def backup(
    service: Services = typer.Argument(..., help="Service name"),
    force: bool = typer.Option(
        False, "--force", help="Force the backup operation", show_default=False,
    ),
):
    Application.controller.controller_init()

    if service == Services.neo4j:
        if not force:
            log.exit(
                "Neo4j backup will stop the container, if running. "
                "If you want to continue add --force flag"
            )
        log.warning("Backup on {} is not implemented", service)

    if service == Services.postgres:
        log.warning("Backup on {} is not implemented", service)
