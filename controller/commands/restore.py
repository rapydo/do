"""
Restore a backup of one service
"""
import time
from enum import Enum
from typing import List, Optional

import typer

from controller import BACKUP_DIR, log, print_and_exit
from controller.app import Application
from controller.commands import RESTORE_MODULES
from controller.deploy.builds import verify_available_images
from controller.deploy.docker import Docker

# Enum() expects a string, tuple, list or dict literal as the second argument
# https://github.com/python/mypy/issues/5317
SupportedServices = Enum(  # type: ignore
    "SupportedServices", {name: name for name in sorted(RESTORE_MODULES.keys())}
)


# Also duplicated in backup.py. A wrapper is needed (to be also used in reload.py)
def reload(docker: Docker, services: List[str]) -> None:
    for service in services:
        containers = docker.get_containers(service)
        docker.exec_command(containers, user="root", command="/usr/local/bin/reload")


@Application.app.command(help="Restore a backup of one service")
def restore(
    service: SupportedServices = typer.Argument(..., help="Service name"),
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

    docker = Docker()

    container = docker.get_container(service_name)

    backup_dir = BACKUP_DIR.joinpath(service_name)
    if not backup_dir.exists():
        print_and_exit(
            "No backup found, the following folder does not exist: {}", backup_dir
        )

    module = RESTORE_MODULES.get(service.value)

    if not module:  # pragma: no cover
        print_and_exit(f"{service.value} misconfiguration, module not found")

    expected_ext = module.EXPECTED_EXT

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

    module.restore(container=container, backup_file=backup_file, force=force)

    if restart:
        log.info("Restarting services in 20 seconds...")
        time.sleep(10)
        log.info("Restarting services in 10 seconds...")
        time.sleep(10)
        reload(docker, restart)
