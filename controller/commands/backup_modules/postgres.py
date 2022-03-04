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

    # This double step is required because postgres user is uid 70
    # It is not fixed with host uid as the other SERVICE_NAMEs
    tmp_backup_path = f"/tmp/{now}.sql"
    # Creating backup on a tmp folder as postgres user
    if not dry_run:
        log.info("Executing pg_dumpall...")
        docker.exec_command(
            container,
            user="postgres",
            command=f"pg_dumpall --clean -U sqluser -f {tmp_backup_path}",
        )

    # Compress the sql with best compression ratio
    if not dry_run:
        log.info("Compressing the backup file...")
        docker.exec_command(
            container, user="postgres", command=f"gzip -9 {tmp_backup_path}"
        )

    # Verify the gz integrity
    if not dry_run:
        log.info("Verifying the integrity of the backup file...")
        docker.exec_command(
            container, user="postgres", command=f"gzip -t {tmp_backup_path}.gz"
        )

    # Move the backup from /tmp to /backup (as root user)
    backup_path = f"/backup/{SERVICE_NAME}/{now}.sql.gz"
    if not dry_run:
        docker.exec_command(
            container, user="root", command=f"mv {tmp_backup_path}.gz {backup_path}"
        )

    log.info("Backup completed: data{}", backup_path)
