"""
Execute a backup of one service
"""
import time
from datetime import datetime
from enum import Enum
from typing import List

import typer

from controller import BACKUP_DIR, log, print_and_exit
from controller.app import Application
from controller.commands import BACKUP_MODULES
from controller.deploy.builds import verify_available_images
from controller.deploy.docker import Docker

# 0 1 * * * cd /home/??? && /usr/local/bin/rapydo backup neo4j --force > \
#         /home/???/data/logs/backup.log 2>&1

# Enum() expects a string, tuple, list or dict literal as the second argument
# https://github.com/python/mypy/issues/5317
SupportedServices = Enum(  # type: ignore
    "SupportedServices", {name: name for name in sorted(BACKUP_MODULES.keys())}
)


# Returned from a function just to be able to easily test it
def get_date_pattern() -> str:
    return (
        "[1-2][0-9][0-9][0-9]_"  # year
        "[0-1][0-9]_"  # month
        "[0-3][0-9]-"  # day
        "[0-2][0-9]_"  # hour
        "[0-5][0-9]_"  # minute
        "[0-5][0-9]"  # second
        ".*"  # extension
    )


# Also duplicated in restore.py. A wrapper is needed (to be also used in reload.py)
def reload(docker: Docker, services: List[str]) -> None:
    for service in services:
        containers = docker.get_containers(service)
        docker.exec_command(containers, user="root", command="/usr/local/bin/reload")


@Application.app.command(help="Execute a backup of one service")
def backup(
    service: SupportedServices = typer.Argument(..., help="Service name"),
    force: bool = typer.Option(
        False,
        "--force",
        help="Force the backup procedure",
        show_default=False,
    ),
    max_backups: int = typer.Option(
        0,
        "--max",
        help="Maximum number of backups, older exceeding this number will be removed",
        show_default=False,
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Do not perform any backup or delete backup files",
        show_default=False,
    ),
    restart: List[str] = typer.Option(
        [],
        "--restart",
        help="Service to be restarted once completed the backup (multiple allowed)",
        shell_complete=Application.autocomplete_service,
    ),
) -> None:

    Application.print_command(
        Application.serialize_parameter("--force", force, IF=force),
        Application.serialize_parameter("--max", max_backups, IF=max_backups),
        Application.serialize_parameter("--dry-run", dry_run, IF=dry_run),
        Application.serialize_parameter("--restart", restart, IF=restart),
        Application.serialize_parameter("", service.value),
    )

    if dry_run:
        log.warning("Dry run mode is enabled")

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
    backup_dir.mkdir(parents=True, exist_ok=True)

    if max_backups > 0:
        backups = list(backup_dir.glob(get_date_pattern()))
        if max_backups >= len(backups):
            log.debug("Found {} backup files, maximum not reached", len(backups))
        else:
            for f in sorted(backups)[:-max_backups]:
                if not dry_run:
                    f.unlink()
                log.warning(
                    "{} deleted because exceeding the max number of backup files ({})",
                    f.name,
                    max_backups,
                )

    module = BACKUP_MODULES.get(service.value)

    if not module:  # pragma: no cover
        print_and_exit(f"{service.value} misconfiguration, module not found")

    now = datetime.now().strftime("%Y_%m_%d-%H_%M_%S")
    module.backup(container=container, now=now, force=force, dry_run=dry_run)

    if restart and not dry_run:
        log.info("Restarting services in 20 seconds...")
        time.sleep(10)
        log.info("Restarting services in 10 seconds...")
        time.sleep(10)
        reload(docker, restart)
