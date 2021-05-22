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
    mariadb = "mariadb"
    rabbit = "rabbit"
    redis = "redis"


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

    service_name = service.value

    options = {"SERVICE": [service_name]}
    dc = Compose(files=Application.data.files)

    running_containers = dc.get_running_containers(Configuration.project)
    container_is_running = service_name in running_containers

    expected_ext = ""

    if service_name == Services.neo4j:
        expected_ext = ".dump"
    elif service_name == Services.postgres:
        expected_ext = ".sql.gz"
    elif service_name == Services.mariadb:
        expected_ext = ".tar.gz"
    elif service_name == Services.rabbit:
        expected_ext = ".tar.gz"
    elif service_name == Services.redis:
        expected_ext = ".tar.gz"

    backup_dir = Path("data").joinpath("backup").joinpath(service_name)
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

    backup_host_path = backup_dir.joinpath(backup_file)
    if not backup_host_path.exists():
        Application.exit("Invalid backup file, {} does not exist", backup_host_path)

    if service_name == Services.neo4j:
        if container_is_running and not force:
            Application.exit(
                "Neo4j is running and the restore will temporary stop it. "
                "If you want to continue add --force flag"
            )

        if container_is_running:
            dc.command("stop", options)

        backup_path = f"/backup/{service_name}/{backup_file}"

        command = f"neo4j-admin load --from={backup_path} --database=neo4j --force"

        log.info("Starting restore on {}...", service_name)

        dc.create_volatile_container(service_name, command=command)

        log.info("Restore from data{} completed", backup_path)

        if container_is_running:
            dc.start_containers([service_name], detach=True)

    if service_name == Services.postgres:

        if not container_is_running:
            Application.exit(
                "The restore procedure requires {} running, please start your stack",
                service_name,
            )

        log.info("Starting restore on {}...", service_name)

        backup_path = f"/backup/{service_name}/{backup_file}"
        dump_file = backup_file.replace(".gz", "")
        dump_path = f"/tmp/{dump_file}"

        command = f"cp {backup_path} /tmp/"
        # Executed as root
        dc.exec_command(service_name, command=command, disable_tty=True)

        command = f"gunzip -kf /tmp/{backup_file}"
        # Executed as root
        dc.exec_command(service_name, command=command, disable_tty=True)

        command = f"chown postgres {dump_path}"
        # Executed as root
        dc.exec_command(service_name, command=command, disable_tty=True)

        # By using pg_dumpall the resulting dump can be restored with psql:
        command = f"psql -U sqluser -f {dump_path} postgres"
        dc.exec_command(
            service_name, command=command, user="postgres", disable_tty=True
        )

        log.info("Restore from data{} completed", backup_path)

    if service_name == Services.mariadb:

        if container_is_running and not force:
            Application.exit(
                "MariaDB is running and the restore will temporary stop it. "
                "If you want to continue add --force flag"
            )

        log.info("Starting restore on {}...", service_name)

        if container_is_running:
            dc.command("stop", options)

        # backup.tar.gz
        backup_path = f"/backup/{service_name}/{backup_file}"

        # backup without tar.gz
        tmp_backup_path = backup_path.replace(".tar.gz", "")

        log.info("Opening backup file")
        # Uncompress /backup/{service_name}/{backup_file} into /backup/{service_name}
        command = f"tar -xf {backup_path} -C /backup/{service_name}"
        dc.create_volatile_container(service_name, command=command)

        log.info("Removing current datadir")
        # mariabackup required the datadir to be empty...
        command = "rm -rf /var/lib/mysql/*"
        # without bash -c   the * does not work...
        command = "bash -c 'rm -rf /var/lib/mysql/*'"
        dc.create_volatile_container(service_name, command=command)

        log.info("Restoring the backup")
        # Note: --move-back moves instead of copying
        # But since some files are preserved and anyway the top level folder has to be
        # manually deleted, it is preferred to use the more conservative copy-back
        # and then delete the whole temporary folder manually
        command = f"sh -c 'mariabackup --copy-back --target-dir={tmp_backup_path}'"
        dc.create_volatile_container(service_name, command=command)

        log.info("Removing the temporary uncompressed folder")
        # Removed the temporary uncompressed folder in /backup/{service_name}
        command = f"rm -rf {tmp_backup_path}"
        dc.create_volatile_container(service_name, command=command)

        if container_is_running:
            dc.start_containers([service_name], detach=True)

        log.info("Restore from data{} completed", backup_path)

    if service_name == Services.rabbit:
        if container_is_running and not force:
            Application.exit(
                "RabbitMQ is running and the restore will temporary stop it. "
                "If you want to continue add --force flag"
            )

        if container_is_running:
            dc.command("stop", options)

        backup_path = f"/backup/{service_name}/{backup_file}"

        command = f"tar -xf {backup_path} -C /var/lib/rabbitmq/"

        log.info("Starting restore on {}...", service_name)

        dc.create_volatile_container(service_name, command=command)

        log.info("Restore from data{} completed", backup_path)

        if container_is_running:
            dc.start_containers([service_name], detach=True)

    if service_name == Services.redis:

        if container_is_running and not force:
            Application.exit(
                "Redis is running and the restore will temporary stop it. "
                "If you want to continue add --force flag"
            )

        if container_is_running:
            dc.command("stop", options)

        backup_path = f"/backup/{service_name}/{backup_file}"
        log.info("Starting restore on {}...", service_name)

        command = f"tar -xf {backup_path} -C /data/"
        dc.create_volatile_container(service_name, command=command)

        log.info("Restore from data{} completed", backup_path)

        if container_is_running:
            dc.start_containers([service_name], detach=True)

    if restart:
        dc.command("restart", {"SERVICE": restart})
