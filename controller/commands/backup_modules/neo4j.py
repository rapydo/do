from datetime import datetime
from typing import Optional, Tuple

from controller import SWARM_MODE, log, print_and_exit
from controller.app import Application
from controller.deploy.compose_v2 import Compose
from controller.deploy.docker import Docker
from controller.deploy.swarm import Swarm

SERVICE_NAME = __name__
EXPECTED_EXT = ".dump"


# Also duplicated in restore.py, backup.neo4j, backup.rabbit. A wrapper is needed
def remove(compose: Compose, service: str) -> None:
    if SWARM_MODE:
        service_name = Docker.get_service(service)
        compose.docker.service.scale({service_name: 0}, detach=False)
    else:
        compose.docker.compose.rm([service], stop=True, volumes=False)


# Also duplicated in restore.py, backup.neo4j, backup.rabbit. A wrapper is needed
def start(compose: Compose, service: str) -> None:
    if SWARM_MODE:
        swarm = Swarm()
        swarm.deploy()
    else:
        compose.start_containers([service])


def backup(
    container: Optional[Tuple[str, str]], now: datetime, force: bool, dry_run: bool
) -> None:
    if container and not force:
        print_and_exit(
            "Neo4j is running and the backup will temporary stop it. "
            "If you want to continue add --force flag"
        )

    compose = Compose(Application.data.files)
    if container and not dry_run:
        remove(compose, SERVICE_NAME)

    backup_path = f"/backup/{SERVICE_NAME}/{now}.dump"

    command = f"neo4j-admin dump --to={backup_path} --database=neo4j"

    log.info("Starting backup on {}...", SERVICE_NAME)
    if not dry_run:
        compose.create_volatile_container(SERVICE_NAME, command=command)

    log.info("Backup completed: data{}", backup_path)

    if container and not dry_run:
        start(compose, SERVICE_NAME)
