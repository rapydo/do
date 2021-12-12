from datetime import datetime
from typing import Optional, Tuple

from controller import SWARM_MODE, log, print_and_exit
from controller.deploy.docker import Docker
from controller.deploy.swarm import Swarm

SERVICE_NAME = __name__
EXPECTED_EXT = ".dump"


# Duplicated in backup and restore modules (neo4j, rabbit, redis ...)
def remove(docker: Docker, service: str) -> None:
    if SWARM_MODE:
        service_name = Docker.get_service(service)
        docker.client.service.scale({service_name: 0}, detach=False)
    else:
        docker.client.compose.rm([service], stop=True, volumes=False)


# Duplicated in backup and restore modules (neo4j, rabbit, redis ...)
def start(docker: Docker, service: str) -> None:
    if SWARM_MODE:
        swarm = Swarm()
        swarm.deploy()
    else:
        docker.compose.start_containers([service])


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
        remove(docker, SERVICE_NAME)

    backup_path = f"/backup/{SERVICE_NAME}/{now}.dump"

    command = f"neo4j-admin dump --to={backup_path} --database=neo4j"

    log.info("Starting backup on {}...", SERVICE_NAME)
    if not dry_run:
        docker.compose.create_volatile_container(SERVICE_NAME, command=command)

    log.info("Backup completed: data{}", backup_path)

    if container and not dry_run:
        start(docker, SERVICE_NAME)
