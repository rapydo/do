from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import List

import typer

from controller import log
from controller.app import Application, Configuration
from controller.compose import Compose

# 0 1 * * * cd /home/??? && \
#     COMPOSE_INTERACTIVE_NO_CLI=1 /usr/local/bin/rapydo backup neo4j --force > \
#         /home/???/data/logs/backup.log 2>&1


class Services(str, Enum):
    neo4j = "neo4j"
    postgres = "postgres"


@Application.app.command(help="Execute a backup of one service")
def backup(
    service: Services = typer.Argument(..., help="Service name"),
    force: bool = typer.Option(
        False,
        "--force",
        help="Force the backup procedure",
        show_default=False,
    ),
    restart: List[str] = typer.Option(
        "",
        "--restart",
        help="Service to be restarted once completed the backup (multiple allowed)",
        autocompletion=Application.autocomplete_service,
    ),
) -> None:
    Application.get_controller().controller_init()

    service_name = service.value

    dc = Compose(files=Application.data.files)

    running_containers = dc.get_running_containers(Configuration.project)
    container_is_running = service_name in running_containers

    backup_dir = Path("data").joinpath("backup")
    backup_dir.joinpath(service_name).mkdir(parents=True, exist_ok=True)

    now = datetime.now().strftime("%Y_%m_%d-%H_%M_%S")
    if service_name == Services.neo4j:
        if container_is_running and not force:
            Application.exit(
                "Neo4j is running and the backup will temporary stop it. "
                "If you want to continue add --force flag"
            )

        if container_is_running:
            dc.command("stop", {"SERVICE": [service_name]})

        backup_path = f"/backup/{service_name}/{now}.dump"

        command = f"neo4j-admin dump --to={backup_path} --database=neo4j"

        log.info("Starting backup on {}...", service_name)
        dc.create_volatile_container(service_name, command=command)

        log.info("Backup completed: data{}", backup_path)

        if container_is_running:
            dc.start_containers([service_name], detach=True)

    if service_name == Services.postgres:

        if not container_is_running:
            Application.exit(
                "The backup procedure requires {} running, please start your stack",
                service_name,
            )

        log.info("Starting backup on {}...", service_name)

        # This double step is required because postgres user is uid 70
        # It is not fixed with host uid as the other service_names
        tmp_backup_path = f"/tmp/{now}.sql"
        command = f"pg_dumpall --clean -U sqluser -f {tmp_backup_path}"
        # Creating backup on a tmp folder as postgres user
        dc.exec_command(
            service_name, command=command, user="postgres", disable_tty=True
        )

        # Compress the sql with best compression ratio
        command = f"gzip -9 {tmp_backup_path}"
        dc.exec_command(
            service_name, command=command, user="postgres", disable_tty=True
        )

        # Verify the gz integrity
        command = f"gzip -t {tmp_backup_path}.gz"
        dc.exec_command(
            service_name, command=command, user="postgres", disable_tty=True
        )

        # Move the backup from /tmp to /backup (as root user)
        backup_path = f"/backup/{service_name}/{now}.sql.gz"
        command = f"mv {tmp_backup_path}.gz {backup_path}"
        dc.exec_command(service_name, command=command, disable_tty=True)

        log.info("Backup completed: data{}", backup_path)

    if restart:
        dc.command("restart", {"SERVICE": restart})
