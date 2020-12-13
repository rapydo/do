from typing import List

import typer

from controller import log
from controller.app import Application


@Application.app.command(help="Update the current project")
def update(
    ignore_submodules: List[str] = typer.Option(
        "",
        "--ignore-submodule",
        "-i",
        help="Ignore a submodule",
        show_default=False,
        autocompletion=Application.autocomplete_submodule,
    ),
) -> None:
    Application.get_controller().controller_init()

    Application.git_update(ignore_submodules)
    # Reading again the configuration, it may change with git updates
    Application.get_controller().read_specs(read_extended=True)

    Application.get_controller().make_env()

    # Compose services and variables
    Application.get_controller().read_composers()
    Application.get_controller().set_active_services()

    Application.get_controller().check_placeholders()

    log.info("All updated")
