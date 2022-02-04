from datetime import datetime
from typing import Optional, Tuple

from controller import log
from controller.deploy.docker import Docker

SERVICE_NAME = __name__


def backup(
    container: Optional[Tuple[str, str]], now: datetime, force: bool, dry_run: bool
) -> None:

    docker = Docker()

    log.info("Starting backup on {}...", SERVICE_NAME)

    backup_path = f"/backup/{SERVICE_NAME}/{now}.tar.gz"
    # If running, ask redis to synchronize the database
    if container:
        docker.exec_command(
            container,
            user="redis",
            command="sh -c 'redis-cli --pass \"$REDIS_PASSWORD\" save'",
        )

    command = f"tar -zcf {backup_path} -C /data dump.rdb appendonly.aof"
    if not dry_run:
        log.info("Compressing the data files...")
        if container:
            docker.exec_command(container, user="redis", command=command)
        else:
            docker.compose.create_volatile_container(SERVICE_NAME, command=command)

    # Verify the gz integrity
    command = f"gzip -t {backup_path}"
    if not dry_run:
        log.info("Verifying the integrity of the backup file...")
        if container:
            docker.exec_command(container, user="redis", command=command)
        else:
            docker.compose.create_volatile_container(SERVICE_NAME, command=command)

    log.info("Backup completed: data{}", backup_path)
