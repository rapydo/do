from typing import List

import typer

from controller import log, print_and_exit
from controller.app import Application, Configuration
from controller.deploy.compose_v2 import Compose


@Application.app.command(help="Stop and remove containers")
def remove(
    services: List[str] = typer.Argument(
        None,
        help="Services to be removed",
        autocompletion=Application.autocomplete_service,
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

    if rm_all:

        if Configuration.services_list is not None or services:

            print_and_exit(
                "Incompatibile options --all and service list\n"
                + "rapydo remove --all is ALWAYS applied to EVERY container of the "
                + "stack due to the underlying docker-compose implementation. "
                + "If you want to continue remove service option",
            )
        else:
            log.warning("--all option not implemented yet")

    # "--volumes": rm_all,
    dc.docker.compose.down(remove_orphans=False, remove_images="local")

    log.info("Stack removed")
