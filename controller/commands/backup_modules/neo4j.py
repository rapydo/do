from datetime import datetime
from typing import Optional, Tuple

from controller import log, print_and_exit
from controller.deploy.docker import Docker

SERVICE_NAME = __name__
EXPECTED_EXT = ".dump"


def backup(
    container: Optional[Tuple[str, str]], now: datetime, force: bool, dry_run: bool
) -> None:
    if container and not force:
        print_and_exit(
            "Neo4j is running and the backup will temporary stop it. "
            "If you want to continue add --force flag"
        )

    docker = Docker()
    if container and not dry_run:
        docker.remove(SERVICE_NAME)

    backup_path = f"/backup/{SERVICE_NAME}/{now}.dump"

    command = f"neo4j-admin dump --to={backup_path} --database=neo4j"

    log.info("Starting backup on {}...", SERVICE_NAME)
    if not dry_run:
        docker.compose.create_volatile_container(SERVICE_NAME, command=command)

    log.info("Backup completed: data{}", backup_path)

    if container and not dry_run:
        docker.start(SERVICE_NAME)
