from typing import List

import typer

from controller import log
from controller.app import Application
from controller.utilities import services


@Application.app.command(help="Update the current project")
def update(
    ignore_submodules: List[str] = typer.Option(
        [],
        "--ignore-submodule",
        "-i",
        help="Ignore a submodule",
        show_default=False,
        shell_complete=Application.autocomplete_submodule,
    ),
) -> None:

    Application.print_command(
        Application.serialize_parameter("--ignore-submodule", ignore_submodules),
    )

    Application.get_controller().controller_init()

    Application.git_update(ignore_submodules)
    # Reading again the configuration, it may change with git updates
    Application.get_controller().read_specs(read_extended=True)

    Application.get_controller().make_env()

    # Compose services and variables
    base_services, config = Application.get_controller().get_compose_configuration()
    active_services = services.find_active(config)

    Application.get_controller().check_placeholders_and_passwords(
        config, active_services
    )

    log.info("All updated")
