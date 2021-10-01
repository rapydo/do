from typing import List

import typer

from controller import log
from controller.app import Application
from controller.deploy.compose_v2 import Compose


@Application.app.command(help="Stop and remove containers")
def remove(
    services: List[str] = typer.Argument(
        None,
        help="Services to be removed",
        shell_complete=Application.autocomplete_service,
    ),
    rm_all: bool = typer.Option(
        False,
        "--all",
        help="Also remove persistent data stored in docker volumes",
        show_default=False,
    ),
) -> None:
    Application.get_controller().controller_init(services)

    dc = Compose(Application.data.files)

    all_services = Application.data.services == Application.data.active_services

    if all_services and rm_all:
        # Networks are not removed, but based on docker compose down --help they should
        # Also docker-compose down removes network from what I remember
        # Should be reported as bug? If corrected a specific check in test_remove.py
        # will start to fail
        dc.docker.compose.down(
            remove_orphans=False,
            remove_images="local",
            # Remove named volumes declared in the volumes section of the
            # Compose file and anonymous volumes attached to containers.
            volumes=rm_all,
        )
    else:
        # Important note: volumes=True only destroy anonymous volumes,
        # not named volumes like down should do
        dc.docker.compose.rm(Application.data.services, stop=True, volumes=rm_all)

    log.info("Stack removed")
