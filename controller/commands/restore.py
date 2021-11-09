import time
from enum import Enum
from pathlib import Path
from typing import List, Optional

import typer

from controller import SWARM_MODE, log, print_and_exit
from controller.app import Application
from controller.deploy.builds import verify_available_images
from controller.deploy.compose_v2 import Compose
from controller.deploy.docker import Docker
from controller.deploy.swarm import Swarm


class Services(str, Enum):
    neo4j = "neo4j"
    postgres = "postgres"
    mariadb = "mariadb"
    rabbit = "rabbit"
    redis = "redis"


# Also duplicated in backup.py. A wrapper is needed
def remove(compose: Compose, service: str) -> None:
    if SWARM_MODE:
        service_name = Docker.get_service(service)
        compose.docker.service.scale({service_name: 0}, detach=False)
    else:
        compose.docker.compose.rm([service], stop=True, volumes=False)


# Also duplicated in backup.py. A wrapper is needed
def start(compose: Compose, service: str) -> None:
    if SWARM_MODE:
        swarm = Swarm()
        swarm.deploy()
    else:
        compose.start_containers([service])


# Also duplicated in backup.py. A wrapper is needed (to be also used in reload.py)
def reload(docker: Docker, services: List[str]) -> None:
    for service in services:
        containers = docker.get_containers(service)
        docker.exec_command(containers, user="root", command="/usr/local/bin/reload")


@Application.app.command(help="Restore a backup of one service")
def restore(
    service: Services = typer.Argument(..., help="Service name"),
    backup_file: Optional[str] = typer.Argument(
        None,
        help="Specify the backup to be restored",
        show_default=False,
    ),
    force: bool = typer.Option(
        False,
        "--force",
        help="Force the backup procedure",
        show_default=False,
    ),
    restart: List[str] = typer.Option(
        [],
        "--restart",
        help="Service to be restarted once completed the restore (multiple allowed)",
        shell_complete=Application.autocomplete_service,
    ),
) -> None:

    Application.print_command(
        Application.serialize_parameter("--force", force, IF=force),
        Application.serialize_parameter("--restart", restart, IF=restart),
        Application.serialize_parameter("", service.value),
        Application.serialize_parameter("", backup_file),
    )
    Application.get_controller().controller_init()

    service_name = service.value

    verify_available_images(
        [service_name],
        Application.data.compose_config,
        Application.data.base_services,
    )

    compose = Compose(Application.data.files)
    docker = Docker()

    container = docker.get_container(service_name)

    expected_ext = ""

    if service_name == Services.neo4j:
        expected_ext = ".dump"
    elif service_name == Services.postgres:
        expected_ext = ".sql.gz"
    elif service_name == Services.mariadb:
        expected_ext = ".tar.gz"
    elif service_name == Services.rabbit:
        expected_ext = ".tar.gz"
    elif service_name == Services.redis:
        expected_ext = ".tar.gz"

    backup_dir = Path("data", "backup", service_name)
    if not backup_dir.exists():
        print_and_exit(
            "No backup found, the following folder does not exist: {}", backup_dir
        )

    if backup_file is None:
        files = backup_dir.iterdir()

        filtered_files = [d.name for d in files if d.name.endswith(expected_ext)]
        filtered_files.sort()

        if not len(filtered_files):
            print_and_exit("No backup found, {} is empty", backup_dir)

        log.info("Please specify one of the following backup:")
        for f in filtered_files:
            print(f"- {f}")

        return

    backup_host_path = backup_dir.joinpath(backup_file)
    if not backup_host_path.exists():
        print_and_exit("Invalid backup file, {} does not exist", backup_host_path)

    if service_name == Services.neo4j:
        if container and not force:
            print_and_exit(
                "Neo4j is running and the restore will temporary stop it. "
                "If you want to continue add --force flag"
            )

        if container:
            remove(compose, service_name)

        backup_path = f"/backup/{service_name}/{backup_file}"

        command = f"neo4j-admin load --from={backup_path} --database=neo4j --force"

        log.info("Starting restore on {}...", service_name)

        compose.create_volatile_container(service_name, command=command)

        log.info("Restore from data{} completed", backup_path)

        if container:
            start(compose, service_name)

    if service_name == Services.postgres:

        if not container:
            print_and_exit(
                "The restore procedure requires {} running, please start your stack",
                service_name,
            )

        log.info("Starting restore on {}...", service_name)

        backup_path = f"/backup/{service_name}/{backup_file}"
        dump_file = backup_file.replace(".gz", "")
        dump_path = f"/tmp/{dump_file}"

        docker.exec_command(container, user="root", command=f"cp {backup_path} /tmp/")

        docker.exec_command(
            container, user="root", command=f"gunzip -kf /tmp/{backup_file}"
        )

        # Executed as root
        docker.exec_command(
            container, user="root", command=f"chown postgres {dump_path}"
        )

        # By using pg_dumpall the resulting dump can be restored with psql:
        docker.exec_command(
            container,
            user="postgres",
            command=f"psql -U sqluser -f {dump_path} postgres",
        )

        log.info("Restore from data{} completed", backup_path)

    if service_name == Services.mariadb:

        if container and not force:
            print_and_exit(
                "MariaDB is running and the restore will temporary stop it. "
                "If you want to continue add --force flag"
            )

        log.info("Starting restore on {}...", service_name)

        if container:
            remove(compose, service_name)

        # backup.tar.gz
        backup_path = f"/backup/{service_name}/{backup_file}"

        # backup without tar.gz
        tmp_backup_path = backup_path.replace(".tar.gz", "")

        log.info("Opening backup file")
        # Uncompress /backup/{service_name}/{backup_file} into /backup/{service_name}
        command = f"tar -xf {backup_path} -C /backup/{service_name}"
        compose.create_volatile_container(service_name, command=command)
        # Debug code: wait the complete container removal, otherwise can fail
        # because the name is still found in use
        # To be replaced with a script inside the container
        time.sleep(1)

        log.info("Removing current datadir")
        # mariabackup required the datadir to be empty...
        command = "rm -rf /var/lib/mysql/*"
        # without bash -c the * does not work...
        command = "bash -c 'rm -rf /var/lib/mysql/*'"
        compose.create_volatile_container(service_name, command=command)
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
        compose.create_volatile_container(service_name, command=command)
        # Debug code: wait the complete container removal, otherwise can fail
        # because the name is still found in use
        # To be replaced with a script inside the container
        time.sleep(1)

        log.info("Removing the temporary uncompressed folder")
        # Removed the temporary uncompressed folder in /backup/{service_name}
        command = f"rm -rf {tmp_backup_path}"
        compose.create_volatile_container(service_name, command=command)
        # Debug code: wait the complete container removal, otherwise can fail
        # because the name is still found in use
        # To be replaced with a script inside the container
        time.sleep(1)

        if container:
            start(compose, service_name)

        log.info("Restore from data{} completed", backup_path)

    if service_name == Services.rabbit:
        if container and not force:
            print_and_exit(
                "RabbitMQ is running and the restore will temporary stop it. "
                "If you want to continue add --force flag"
            )

        if container:
            remove(compose, service_name)

        backup_path = f"/backup/{service_name}/{backup_file}"

        command = f"tar -xf {backup_path} -C /var/lib/rabbitmq/"

        log.info("Starting restore on {}...", service_name)

        compose.create_volatile_container(service_name, command=command)

        log.info("Restore from data{} completed", backup_path)

        if container:
            start(compose, service_name)

    if service_name == Services.redis:

        if container and not force:
            print_and_exit(
                "Redis is running and the restore will temporary stop it. "
                "If you want to continue add --force flag"
            )

        if container:
            remove(compose, service_name)

        backup_path = f"/backup/{service_name}/{backup_file}"
        log.info("Starting restore on {}...", service_name)

        command = f"tar -xf {backup_path} -C /data/"
        compose.create_volatile_container(service_name, command=command)

        log.info("Restore from data{} completed", backup_path)

        if container:
            start(compose, service_name)

    if restart:
        reload(docker, restart)
