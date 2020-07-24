from datetime import datetime
from enum import Enum
from pathlib import Path

import typer

from controller import log
from controller.app import Application
from controller.compose import Compose


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

    backup_dir = Path("data").joinpath("backup")
    service = service.value

    if service == Services.neo4j:
        if not force:
            log.exit(
                "Neo4j backup will stop the container, if running. "
                "If you want to continue add --force flag"
            )

        options = {"SERVICE": [service]}
        dc = Compose(files=Application.data.files)

        running_containers = dc.get_running_containers("imc")
        container_is_running = service in running_containers

        if container_is_running:
            dc.command("stop", options)

        backup_dir.joinpath(service).mkdir(parents=True, exist_ok=True)

        log.info("Starting backup on {}...", service)
        now = datetime.now().strftime("%Y_%m_%d-%H_%M_%S")
        backup_path = f"/backup/{service}/{now}.tar.gz"
        command = f"tar -zcf {backup_path} /data"
        dc.create_volatile_container(service, command=command)

        log.info("Backup completed: data{}", backup_path)

        if container_is_running:
            dc.start_containers([service], detach=True)

    if service == Services.postgres:
        log.warning("Backup on {} is not implemented", service)
