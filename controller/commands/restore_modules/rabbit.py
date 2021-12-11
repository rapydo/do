from typing import Optional, Tuple

from controller import SWARM_MODE, log, print_and_exit
from controller.app import Application
from controller.deploy.compose_v2 import Compose
from controller.deploy.docker import Docker
from controller.deploy.swarm import Swarm

SERVICE_NAME = __name__
EXPECTED_EXT = ".tar.gz"


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


def restore(
    container: Optional[Tuple[str, str]], backup_file: str, force: bool
) -> None:

    if container and not force:
        print_and_exit(
            "RabbitMQ is running and the restore will temporary stop it. "
            "If you want to continue add --force flag"
        )

    compose = Compose(Application.data.files)

    if container:
        remove(compose, SERVICE_NAME)

    backup_path = f"/backup/{SERVICE_NAME}/{backup_file}"

    command = f"tar -xf {backup_path} -C /var/lib/rabbitmq/"

    log.info("Starting restore on {}...", SERVICE_NAME)

    compose.create_volatile_container(SERVICE_NAME, command=command)

    log.info("Restore from data{} completed", backup_path)

    if container:
        start(compose, SERVICE_NAME)
