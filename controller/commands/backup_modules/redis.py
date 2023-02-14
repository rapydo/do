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

    # Backing up AOF persistence
    # https://redis.io/docs/manual/persistence/#backing-up-aof-persistence
    # 1. Turn off automatic rewrites
    # 2. Copy the files in the appenddirname directory
    # 3. Re-enable rewrites
    # Note: Assuming auto-aof-rewrite-percentage is set with its default value (100)

    if container:
        docker.exec_command(
            container,
            user="redis",
            command="sh -c 'redis-cli --pass \"$REDIS_PASSWORD\" CONFIG SET auto-aof-rewrite-percentage 0'",  # noqa
        )

    command = f"tar -zcf {backup_path} -C /data dump.rdb appendonlydir"
    if not dry_run:
        log.info("Compressing the data files...")
        if container:
            docker.exec_command(container, user="redis", command=command)
        else:
            docker.compose.create_volatile_container(SERVICE_NAME, command=command)

    if container:
        docker.exec_command(
            container,
            user="redis",
            command="sh -c 'redis-cli --pass \"$REDIS_PASSWORD\" CONFIG SET auto-aof-rewrite-percentage 100'",  # noqa
        )

    # Verify the gz integrity
    command = f"gzip -t {backup_path}"
    if not dry_run:
        log.info("Verifying the integrity of the backup file...")
        if container:
            docker.exec_command(container, user="redis", command=command)
        else:
            docker.compose.create_volatile_container(SERVICE_NAME, command=command)

    log.info("Backup completed: data{}", backup_path)
