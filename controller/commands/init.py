import os

import typer

from controller import log
from controller.app import Application, Configuration
from controller.utilities import services


@Application.app.command(help="Initialize current RAPyDo project")
def init(
    create_projectrc: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Overwrite initialization files if already exist",
        show_default=False,
    ),
    submodules_path: str = typer.Option(
        None,
        "--submodules-path",
        help="Link all submodules in an existing folder instead of download them",
    ),
):

    for p in Application.data.project_scaffold.data_folders:
        if not os.path.isdir(p):
            os.makedirs(p)

    for p in Application.data.project_scaffold.data_files:
        if not os.path.exists(p):
            open(p, "a").close()

    if not Configuration.projectrc:
        create_projectrc = True

    # We have to create the .projectrc twice
    # One generic here with main options and another after the complete
    # conf reading to set services variables
    if create_projectrc:
        Application.controller.create_projectrc()

    if submodules_path is not None:
        if not os.path.exists(submodules_path):
            log.exit("Local path not found: {}", submodules_path)

    Application.controller.git_submodules(from_path=submodules_path)

    Application.controller.make_env()

    # Compose services and variables
    Application.controller.read_composers()
    Application.controller.set_active_services()
    # We have to create the .projectrc twice
    # One generic with main options and another here
    # when services are available to set specific configurations
    if create_projectrc:
        Application.controller.create_projectrc()
        Application.controller.make_env()
        # Read again! :-(
    #     Application.controller.read_composers()
    #     Application.controller.set_active_services()

    # Application.controller.check_placeholders()
    log.info("Project initialized")
