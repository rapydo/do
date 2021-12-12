from datetime import datetime
from typing import Optional, Tuple

from controller import log, print_and_exit
from controller.deploy.docker import Docker

SERVICE_NAME = __name__


def backup(
    container: Optional[Tuple[str, str]], now: datetime, force: bool, dry_run: bool
) -> None:
    if container and not force:
        print_and_exit(
            "RabbitMQ is running and the backup will temporary stop it. "
            "If you want to continue add --force flag"
        )

    docker = Docker()

    if container and not dry_run:
        docker.remove(SERVICE_NAME)

    backup_path = f"/backup/{SERVICE_NAME}/{now}.tar.gz"

    command = f"tar -zcf {backup_path} -C /var/lib/rabbitmq mnesia"

    log.info("Starting backup on {}...", SERVICE_NAME)
    if not dry_run:
        docker.compose.create_volatile_container(SERVICE_NAME, command=command)

    # Verify the gz integrity
    command = f"gzip -t {backup_path}"

    if not dry_run:
        docker.compose.create_volatile_container(SERVICE_NAME, command=command)

    log.info("Backup completed: data{}", backup_path)

    if container and not dry_run:
        docker.start(SERVICE_NAME)
