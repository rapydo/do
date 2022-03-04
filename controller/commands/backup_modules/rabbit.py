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

    log.info("Starting backup on {}...", SERVICE_NAME)
    if not dry_run:
        log.info("Executing rabbitmq mnesia...")
        docker.compose.create_volatile_container(
            SERVICE_NAME, command=f"tar -zcf {backup_path} -C /var/lib/rabbitmq mnesia"
        )

    # Verify the gz integrity
    if not dry_run:
        log.info("Verifying the integrity of the backup file...")
        docker.compose.create_volatile_container(
            SERVICE_NAME, command=f"gzip -t {backup_path}"
        )

    log.info("Backup completed: data{}", backup_path)

    if container and not dry_run:
        docker.start(SERVICE_NAME)
