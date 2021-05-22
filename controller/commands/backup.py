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
    mariadb = "mariadb"
    rabbit = "rabbit"
    redis = "redis"


# Returned from a function just to be able to easily test it
def get_date_pattern():
    return (
        "[1-2][0-9][0-9][0-9]_"  # year
        "[0-1][0-9]_"  # month
        "[0-3][0-9]-"  # day
        "[0-2][0-9]_"  # hour
        "[0-5][0-9]_"  # minute
        "[0-5][0-9]"  # second
        ".*"  # extension
    )


@Application.app.command(help="Execute a backup of one service")
def backup(
    service: Services = typer.Argument(..., help="Service name"),
    force: bool = typer.Option(
        False,
        "--force",
        help="Force the backup procedure",
        show_default=False,
    ),
    max_backups: int = typer.Option(
        0,
        "--max",
        help="Maximum number of backups, older exceeding this number will be removed",
        show_default=False,
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Do not perform any backup or delete backup files",
        show_default=False,
    ),
    restart: List[str] = typer.Option(
        "",
        "--restart",
        help="Service to be restarted once completed the backup (multiple allowed)",
        autocompletion=Application.autocomplete_service,
    ),
) -> None:

    if dry_run:
        log.warning("Dry run mode is enabled")

    Application.get_controller().controller_init()

    service_name = service.value

    dc = Compose(files=Application.data.files)

    running_containers = dc.get_running_containers(Configuration.project)
    container_is_running = service_name in running_containers

    backup_dir = Path("data").joinpath("backup").joinpath(service_name)
    backup_dir.mkdir(parents=True, exist_ok=True)

    if max_backups > 0:
        backups = list(backup_dir.glob(get_date_pattern()))
        if max_backups >= len(backups):
            log.debug("Found {} backup files, maximum not reached", len(backups))
        else:
            for f in sorted(backups)[:-max_backups]:
                if not dry_run:
                    f.unlink()
                log.warning(
                    "{} deleted because exceeding the max number of backup files ({})",
                    f.name,
                    max_backups,
                )

    now = datetime.now().strftime("%Y_%m_%d-%H_%M_%S")
    if service_name == Services.neo4j:
        if container_is_running and not force:
            Application.exit(
                "Neo4j is running and the backup will temporary stop it. "
                "If you want to continue add --force flag"
            )

        if container_is_running and not dry_run:
            dc.command("stop", {"SERVICE": [service_name]})

        backup_path = f"/backup/{service_name}/{now}.dump"

        command = f"neo4j-admin dump --to={backup_path} --database=neo4j"

        log.info("Starting backup on {}...", service_name)
        if not dry_run:
            dc.create_volatile_container(service_name, command=command)

        log.info("Backup completed: data{}", backup_path)

        if container_is_running and not dry_run:
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
        if not dry_run:
            dc.exec_command(
                service_name, command=command, user="postgres", disable_tty=True
            )

        # Compress the sql with best compression ratio
        command = f"gzip -9 {tmp_backup_path}"
        if not dry_run:
            dc.exec_command(
                service_name, command=command, user="postgres", disable_tty=True
            )

        # Verify the gz integrity
        command = f"gzip -t {tmp_backup_path}.gz"
        if not dry_run:
            dc.exec_command(
                service_name, command=command, user="postgres", disable_tty=True
            )

        # Move the backup from /tmp to /backup (as root user)
        backup_path = f"/backup/{service_name}/{now}.sql.gz"
        command = f"mv {tmp_backup_path}.gz {backup_path}"
        if not dry_run:
            dc.exec_command(service_name, command=command, disable_tty=True)

        log.info("Backup completed: data{}", backup_path)

    if service_name == Services.mariadb:

        if not container_is_running:
            Application.exit(
                "The backup procedure requires {} running, please start your stack",
                service_name,
            )

        log.info("Starting backup on {}...", service_name)

        tmp_backup_path = f"/tmp/{now}"
        command = f"sh -c 'mariabackup --backup --target-dir={tmp_backup_path} "
        command += '-uroot -p"$MYSQL_ROOT_PASSWORD"\''

        # Creating backup on a tmp folder as mysql user
        if not dry_run:
            dc.exec_command(
                service_name, command=command, user="mysql", disable_tty=True
            )

        command = f"sh -c 'mariabackup --prepare --target-dir={tmp_backup_path}'"

        # Creating backup on a tmp folder as mysql user
        if not dry_run:
            dc.exec_command(
                service_name, command=command, user="mysql", disable_tty=True
            )

        # Compress the prepared data folder. Used -C to skip the /tmp from folders paths
        command = f"tar -zcf {tmp_backup_path}.tar.gz -C /tmp {now}"

        if not dry_run:
            dc.exec_command(
                service_name, command=command, user="mysql", disable_tty=True
            )

        # Verify the gz integrity
        command = f"gzip -t {tmp_backup_path}.tar.gz"

        if not dry_run:
            dc.exec_command(
                service_name, command=command, user="mysql", disable_tty=True
            )

        # Move the backup from /tmp to /backup (as root user)
        backup_path = f"/backup/{service_name}/{now}.tar.gz"
        command = f"mv {tmp_backup_path}.tar.gz {backup_path}"

        if not dry_run:
            dc.exec_command(service_name, command=command, disable_tty=True)

        log.info("Backup completed: data{}", backup_path)

    if service_name == Services.rabbit:
        if container_is_running and not force:
            Application.exit(
                "RabbitMQ is running and the backup will temporary stop it. "
                "If you want to continue add --force flag"
            )

        if container_is_running and not dry_run:
            dc.command("stop", {"SERVICE": [service_name]})

        backup_path = f"/backup/{service_name}/{now}.tar.gz"

        command = f"tar -zcf {backup_path} -C /var/lib/rabbitmq mnesia"

        log.info("Starting backup on {}...", service_name)
        if not dry_run:
            dc.create_volatile_container(service_name, command=command)

        # Verify the gz integrity
        command = f"gzip -t {backup_path}"

        if not dry_run:
            dc.create_volatile_container(service_name, command=command)

        log.info("Backup completed: data{}", backup_path)

        if container_is_running and not dry_run:
            dc.start_containers([service_name], detach=True)

    if service_name == Services.redis:

        backup_path = f"/backup/{service_name}/{now}.tar.gz"

        log.info("Starting backup on {}...", service_name)
        # If running, ask redis to synchronize the database
        if container_is_running:
            command = "sh -c 'redis-cli --pass \"$REDIS_PASSWORD\" save'"
            dc.exec_command(service_name, command=command, disable_tty=True)

        command = f"tar -zcf {backup_path} -C /data dump.rdb appendonly.aof"
        if not dry_run:
            if container_is_running:
                dc.exec_command(service_name, command=command, disable_tty=True)
            else:
                dc.create_volatile_container(service_name, command=command)

        # Verify the gz integrity
        command = f"gzip -t {backup_path}"
        if not dry_run:
            if container_is_running:
                dc.exec_command(service_name, command=command, disable_tty=True)
            else:
                dc.create_volatile_container(service_name, command=command)

        log.info("Backup completed: data{}", backup_path)

    if restart and not dry_run:
        dc.command("restart", {"SERVICE": restart})
