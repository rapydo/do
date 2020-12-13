import os
from enum import Enum
from pathlib import Path
from typing import List, Optional

import typer

from controller import log
from controller.app import Application, Configuration
from controller.compose import Compose


class Services(str, Enum):
    neo4j = "neo4j"
    postgres = "postgres"


@Application.app.command(help="Restore a backup of one service")
def restore(
    service: Services = typer.Argument(..., help="Service name"),
    backup_file: Optional[str] = typer.Argument(
        None,
        help="Specify the backup to be restored",
        show_default=False,
    ),
    force: bool = typer.Option(
        False,
        "--force",
        help="Force the backup procedure",
        show_default=False,
    ),
    restart: List[str] = typer.Option(
        "",
        "--restart",
        help="Service to be restarted once completed the restore (multiple allowed)",
        autocompletion=Application.autocomplete_service,
    ),
) -> None:
    Application.get_controller().controller_init()

    service = service.value

    options = {"SERVICE": [service]}
    dc = Compose(files=Application.data.files)

    running_containers = dc.get_running_containers(Configuration.project)
    container_is_running = service in running_containers

    expected_ext = ""

    if service == Services.neo4j:
        expected_ext = ".dump"
    elif service == Services.postgres:
        expected_ext = ".sql.gz"

    backup_dir = Path("data").joinpath("backup").joinpath(service)
    if not backup_dir.exists():
        Application.exit(
            "No backup found, the following folder does not exist: {}", backup_dir
        )

    if backup_file is None:
        files = os.listdir(backup_dir)

        filtered_files = [d for d in files if d.endswith(expected_ext)]
        filtered_files.sort()

        if not len(filtered_files):
            Application.exit("No backup found, {} is empty", backup_dir)

        log.info("Please specify one of the following backup:")
        for f in filtered_files:
            print(f"- {f}")

        return

    # walrus!
    backup_host_path = backup_dir.joinpath(backup_file)
    if not backup_host_path.exists():
        Application.exit("Invalid backup file, {} does not exist", backup_host_path)

    if service == Services.neo4j:
        if container_is_running and not force:
            Application.exit(
                "Neo4j is running and the restore will temporary stop it. "
                "If you want to continue add --force flag"
            )

        if container_is_running:
            dc.command("stop", options)

        backup_path = f"/backup/{service}/{backup_file}"

        command = f"neo4j-admin load --from={backup_path} --database=neo4j --force"

        log.info("Starting restore on {}...", service)

        dc.create_volatile_container(service, command=command)

        log.info("Restore from data{} completed", backup_path)

        if container_is_running:
            dc.start_containers([service], detach=True)

    if service == Services.postgres:

        if not container_is_running:
            Application.exit(
                "The restore procedure requires {} running, please start your stack",
                service,
            )

        log.info("Starting restore on {}...", service)

        backup_path = f"/backup/{service}/{backup_file}"
        dump_file = backup_file.replace(".gz", "")
        dump_path = f"/tmp/{dump_file}"

        command = f"cp {backup_path} /tmp/"
        # Executed as root
        dc.exec_command(service, command=command, disable_tty=True)

        command = f"gunzip -kf /tmp/{backup_file}"
        # Executed as root
        dc.exec_command(service, command=command, disable_tty=True)

        command = f"chown postgres {dump_path}"
        # Executed as root
        dc.exec_command(service, command=command, disable_tty=True)

        # By using pg_dumpall the resulting dump can be restored with psql:
        command = f"psql -U sqluser -f {dump_path} postgres"
        dc.exec_command(service, command=command, user="postgres", disable_tty=True)

        log.info("Restore from data{} completed", backup_path)

    if restart:
        dc.command("restart", {"SERVICE": restart})
