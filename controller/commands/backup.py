from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import List

import typer

from controller import SWARM_MODE, log, print_and_exit
from controller.app import Application
from controller.deploy.builds import verify_available_images
from controller.deploy.compose_v2 import Compose
from controller.deploy.docker import Docker
from controller.deploy.swarm import Swarm

# 0 1 * * * cd /home/??? && /usr/local/bin/rapydo backup neo4j --force > \
#         /home/???/data/logs/backup.log 2>&1


class Services(str, Enum):
    neo4j = "neo4j"
    postgres = "postgres"
    mariadb = "mariadb"
    rabbit = "rabbit"
    redis = "redis"


# Returned from a function just to be able to easily test it
def get_date_pattern() -> str:
    return (
        "[1-2][0-9][0-9][0-9]_"  # year
        "[0-1][0-9]_"  # month
        "[0-3][0-9]-"  # day
        "[0-2][0-9]_"  # hour
        "[0-5][0-9]_"  # minute
        "[0-5][0-9]"  # second
        ".*"  # extension
    )


# Also duplicated in restore.py. A wrapper is needed
def remove(compose: Compose, service: str) -> None:
    if SWARM_MODE:
        service_name = Docker.get_service(service)
        compose.docker.service.scale({service_name: 0}, detach=False)
    else:
        compose.docker.compose.rm([service], stop=True, volumes=False)


# Also duplicated in restore.py. A wrapper is needed
def start(compose: Compose, service: str) -> None:
    if SWARM_MODE:
        swarm = Swarm()
        swarm.deploy()
    else:
        compose.start_containers([service])


# Also duplicated in restore.py. A wrapper is needed (to be also used in reload.py)
def reload(docker: Docker, services: List[str]) -> None:
    for service in services:
        containers = docker.get_containers(service)
        docker.exec_command(containers, user="root", command="/usr/local/bin/reload")


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
        [],
        "--restart",
        help="Service to be restarted once completed the backup (multiple allowed)",
        shell_complete=Application.autocomplete_service,
    ),
) -> None:

    Application.print_command(
        Application.serialize_parameter("--force", force, IF=force),
        Application.serialize_parameter("--max", max_backups, IF=max_backups),
        Application.serialize_parameter("--dry-run", dry_run, IF=dry_run),
        Application.serialize_parameter("--restart", restart, IF=restart),
        Application.serialize_parameter("", service.value),
    )

    if dry_run:
        log.warning("Dry run mode is enabled")

    Application.get_controller().controller_init()

    service_name = service.value

    verify_available_images(
        [service_name],
        Application.data.compose_config,
        Application.data.base_services,
    )

    compose = Compose(Application.data.files)
    docker = Docker()

    container = docker.get_container(service_name)

    backup_dir = Path("data", "backup", service_name)
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
        if container and not force:
            print_and_exit(
                "Neo4j is running and the backup will temporary stop it. "
                "If you want to continue add --force flag"
            )

        if container and not dry_run:
            remove(compose, service_name)

        backup_path = f"/backup/{service_name}/{now}.dump"

        command = f"neo4j-admin dump --to={backup_path} --database=neo4j"

        log.info("Starting backup on {}...", service_name)
        if not dry_run:
            compose.create_volatile_container(service_name, command=command)

        log.info("Backup completed: data{}", backup_path)

        if container and not dry_run:
            start(compose, service_name)

    if service_name == Services.postgres:

        if not container:
            print_and_exit(
                "The backup procedure requires {} running, please start your stack",
                service_name,
            )

        log.info("Starting backup on {}...", service_name)

        # This double step is required because postgres user is uid 70
        # It is not fixed with host uid as the other service_names
        tmp_backup_path = f"/tmp/{now}.sql"
        # Creating backup on a tmp folder as postgres user
        if not dry_run:
            docker.exec_command(
                container,
                user="postgres",
                command=f"pg_dumpall --clean -U sqluser -f {tmp_backup_path}",
            )

        # Compress the sql with best compression ratio
        if not dry_run:
            docker.exec_command(
                container, user="postgres", command=f"gzip -9 {tmp_backup_path}"
            )

        # Verify the gz integrity
        if not dry_run:
            docker.exec_command(
                container, user="postgres", command=f"gzip -t {tmp_backup_path}.gz"
            )

        # Move the backup from /tmp to /backup (as root user)
        backup_path = f"/backup/{service_name}/{now}.sql.gz"
        if not dry_run:
            docker.exec_command(
                container, user="root", command=f"mv {tmp_backup_path}.gz {backup_path}"
            )

        log.info("Backup completed: data{}", backup_path)

    if service_name == Services.mariadb:

        if not container:
            print_and_exit(
                "The backup procedure requires {} running, please start your stack",
                service_name,
            )

        log.info("Starting backup on {}...", service_name)

        tmp_backup_path = f"/tmp/{now}"
        command = f"sh -c 'mariabackup --backup --target-dir={tmp_backup_path} "
        command += '-uroot -p"$MYSQL_ROOT_PASSWORD"\''

        # Creating backup on a tmp folder as mysql user
        if not dry_run:
            docker.exec_command(container, user="mysql", command=command)

        # Creating backup on a tmp folder as mysql user
        if not dry_run:
            docker.exec_command(
                container,
                user="mysql",
                command=f"sh -c 'mariabackup --prepare --target-dir={tmp_backup_path}'",
            )

        # Compress the prepared data folder. Used -C to skip the /tmp from folders paths
        if not dry_run:
            docker.exec_command(
                container,
                user="mysql",
                command=f"tar -zcf {tmp_backup_path}.tar.gz -C /tmp {now}",
            )

        # Verify the gz integrity
        if not dry_run:
            docker.exec_command(
                container, user="mysql", command=f"gzip -t {tmp_backup_path}.tar.gz"
            )

        # Move the backup from /tmp to /backup (as root user)
        backup_path = f"/backup/{service_name}/{now}.tar.gz"
        if not dry_run:
            docker.exec_command(
                container,
                user="root",
                command=f"mv {tmp_backup_path}.tar.gz {backup_path}",
            )

        log.info("Backup completed: data{}", backup_path)

    if service_name == Services.rabbit:
        if container and not force:
            print_and_exit(
                "RabbitMQ is running and the backup will temporary stop it. "
                "If you want to continue add --force flag"
            )

        if container and not dry_run:
            remove(compose, service_name)

        backup_path = f"/backup/{service_name}/{now}.tar.gz"

        command = f"tar -zcf {backup_path} -C /var/lib/rabbitmq mnesia"

        log.info("Starting backup on {}...", service_name)
        if not dry_run:
            compose.create_volatile_container(service_name, command=command)

        # Verify the gz integrity
        command = f"gzip -t {backup_path}"

        if not dry_run:
            compose.create_volatile_container(service_name, command=command)

        log.info("Backup completed: data{}", backup_path)

        if container and not dry_run:
            start(compose, service_name)

    if service_name == Services.redis:

        backup_path = f"/backup/{service_name}/{now}.tar.gz"

        log.info("Starting backup on {}...", service_name)
        # If running, ask redis to synchronize the database
        if container:
            docker.exec_command(
                container,
                user="root",
                command="sh -c 'redis-cli --pass \"$REDIS_PASSWORD\" save'",
            )

        command = f"tar -zcf {backup_path} -C /data dump.rdb appendonly.aof"
        if not dry_run:
            if container:
                docker.exec_command(container, user="root", command=command)
            else:
                compose.create_volatile_container(service_name, command=command)

        # Verify the gz integrity
        command = f"gzip -t {backup_path}"
        if not dry_run:
            if container:
                docker.exec_command(container, user="root", command=command)
            else:
                compose.create_volatile_container(service_name, command=command)

        log.info("Backup completed: data{}", backup_path)

    if restart and not dry_run:
        reload(docker, restart)
