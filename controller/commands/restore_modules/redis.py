from typing import Optional, Tuple

from controller import SWARM_MODE, log, print_and_exit
from controller.deploy.docker import Docker

SERVICE_NAME = __name__
EXPECTED_EXT = ".tar.gz"


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
        docker.swarm.deploy()
    else:
        docker.compose.start_containers([service])


def restore(
    container: Optional[Tuple[str, str]], backup_file: str, force: bool
) -> None:

    if container and not force:
        print_and_exit(
            "Redis is running and the restore will temporary stop it. "
            "If you want to continue add --force flag"
        )

    docker = Docker()

    if container:
        remove(docker, SERVICE_NAME)

    backup_path = f"/backup/{SERVICE_NAME}/{backup_file}"
    log.info("Starting restore on {}...", SERVICE_NAME)

    command = f"tar -xf {backup_path} -C /data/"
    docker.compose.create_volatile_container(SERVICE_NAME, command=command)

    log.info("Restore from data{} completed", backup_path)

    if container:
        start(docker, SERVICE_NAME)
