import time
from typing import Optional, Tuple

from controller import SWARM_MODE, log, print_and_exit
from controller.deploy.docker import Docker
from controller.deploy.swarm import Swarm

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
        swarm = Swarm()
        swarm.deploy()
    else:
        docker.compose.start_containers([service])


def restore(
    container: Optional[Tuple[str, str]], backup_file: str, force: bool
) -> None:

    if container and not force:
        print_and_exit(
            "MariaDB is running and the restore will temporary stop it. "
            "If you want to continue add --force flag"
        )

    docker = Docker()

    log.info("Starting restore on {}...", SERVICE_NAME)

    if container:
        remove(docker, SERVICE_NAME)

    # backup.tar.gz
    backup_path = f"/backup/{SERVICE_NAME}/{backup_file}"

    # backup without tar.gz
    tmp_backup_path = backup_path.replace(".tar.gz", "")

    log.info("Opening backup file")
    # Uncompress /backup/{SERVICE_NAME}/{backup_file} into /backup/{SERVICE_NAME}
    command = f"tar -xf {backup_path} -C /backup/{SERVICE_NAME}"
    docker.compose.create_volatile_container(SERVICE_NAME, command=command)
    # Debug code: wait the complete container removal, otherwise can fail
    # because the name is still found in use
    # To be replaced with a script inside the container
    time.sleep(1)

    log.info("Removing current datadir")
    # mariabackup required the datadir to be empty...
    command = "rm -rf /var/lib/mysql/*"
    # without bash -c the * does not work...
    command = "bash -c 'rm -rf /var/lib/mysql/*'"
    docker.compose.create_volatile_container(SERVICE_NAME, command=command)
    # Debug code: wait the complete container removal, otherwise can fail
    # because the name is still found in use
    # To be replaced with a script inside the container
    time.sleep(1)

    log.info("Restoring the backup")
    # Note: --move-back moves instead of copying
    # But since some files are preserved and anyway the top level folder has to be
    # manually deleted, it is preferred to use the more conservative copy-back
    # and then delete the whole temporary folder manually
    command = f"sh -c 'mariabackup --copy-back --target-dir={tmp_backup_path}'"
    docker.compose.create_volatile_container(SERVICE_NAME, command=command)
    # Debug code: wait the complete container removal, otherwise can fail
    # because the name is still found in use
    # To be replaced with a script inside the container
    time.sleep(1)

    log.info("Removing the temporary uncompressed folder")
    # Removed the temporary uncompressed folder in /backup/{SERVICE_NAME}
    command = f"rm -rf {tmp_backup_path}"
    docker.compose.create_volatile_container(SERVICE_NAME, command=command)
    # Debug code: wait the complete container removal, otherwise can fail
    # because the name is still found in use
    # To be replaced with a script inside the container
    time.sleep(1)

    if container:
        start(docker, SERVICE_NAME)

    log.info("Restore from data{} completed", backup_path)
