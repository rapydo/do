from datetime import datetime
from typing import Optional, Tuple

from controller import log, print_and_exit
from controller.deploy.docker import Docker

SERVICE_NAME = __name__


def backup(
    container: Optional[Tuple[str, str]], now: datetime, force: bool, dry_run: bool
) -> None:
    if not container:
        print_and_exit(
            "The backup procedure requires {} running, please start your stack",
            SERVICE_NAME,
        )

    docker = Docker()

    log.info("Starting backup on {}...", SERVICE_NAME)

    tmp_backup_path = f"/tmp/{now}"
    command = f"sh -c 'mariabackup --backup --target-dir={tmp_backup_path} "
    command += '-uroot -p"$MYSQL_ROOT_PASSWORD"\''

    # Creating backup on a tmp folder as mysql user
    if not dry_run:
        docker.exec_command(container, user="mysql", command=command)

    # Creating backup on a tmp folder as mysql user
    if not dry_run:
        log.info("Executing mariabackup...")
        docker.exec_command(
            container,
            user="mysql",
            command=f"sh -c 'mariabackup --prepare --target-dir={tmp_backup_path}'",
        )

    # Compress the prepared data folder. Used -C to skip the /tmp from folders paths
    if not dry_run:
        log.info("Compressing the backup file...")
        docker.exec_command(
            container,
            user="mysql",
            command=f"tar -zcf {tmp_backup_path}.tar.gz -C /tmp {now}",
        )

    # Verify the gz integrity
    if not dry_run:
        log.info("Verifying the integrity of the backup file...")
        docker.exec_command(
            container, user="mysql", command=f"gzip -t {tmp_backup_path}.tar.gz"
        )

    # Move the backup from /tmp to /backup (as root user)
    backup_path = f"/backup/{SERVICE_NAME}/{now}.tar.gz"
    if not dry_run:
        docker.exec_command(
            container,
            user="root",
            command=f"mv {tmp_backup_path}.tar.gz {backup_path}",
        )

    log.info("Backup completed: data{}", backup_path)
