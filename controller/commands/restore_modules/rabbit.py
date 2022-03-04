from typing import Optional, Tuple

from controller import log, print_and_exit
from controller.deploy.docker import Docker

SERVICE_NAME = __name__
EXPECTED_EXT = ".tar.gz"


def restore(
    container: Optional[Tuple[str, str]], backup_file: str, force: bool
) -> None:

    if container and not force:
        print_and_exit(
            "RabbitMQ is running and the restore will temporary stop it. "
            "If you want to continue add --force flag"
        )

    docker = Docker()

    if container:
        docker.remove(SERVICE_NAME)

    backup_path = f"/backup/{SERVICE_NAME}/{backup_file}"

    command = f"tar -xf {backup_path} -C /var/lib/rabbitmq/"

    log.info("Starting restore on {}...", SERVICE_NAME)

    docker.compose.create_volatile_container(SERVICE_NAME, command=command)

    log.info("Restore from data{} completed", backup_path)

    if container:
        docker.start(SERVICE_NAME)
