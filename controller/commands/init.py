from pathlib import Path

import typer

from controller import log
from controller.app import Application, Configuration


@Application.app.command(help="Initialize current RAPyDo project")
def init(
    create_projectrc: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Overwrite initialization files if already exist",
        show_default=False,
    ),
    submodules_path: Path = typer.Option(
        None,
        "--submodules-path",
        help="Link all submodules in an existing folder instead of download them",
    ),
) -> None:
    Application.get_controller().controller_init()

    for p in Application.project_scaffold.data_folders:
        if not p.exists():
            p.mkdir(parents=True, exist_ok=True)

    for p in Application.project_scaffold.data_files:
        if not p.exists():
            p.touch()

    if not Configuration.projectrc and not Configuration.host_configuration:
        create_projectrc = True

    # We have to create the .projectrc twice
    # One generic here with main options and another after the complete
    # conf reading to set services variables
    if create_projectrc:
        Application.get_controller().create_projectrc()
        Application.get_controller().read_specs(read_extended=False)

    if submodules_path is not None:
        if not submodules_path.exists():
            Application.exit("Local path not found: {}", submodules_path)

    Application.git_submodules(from_path=submodules_path)

    Application.get_controller().read_specs(read_extended=True)
    Application.get_controller().make_env()

    # Compose services and variables
    Application.get_controller().read_composers()
    Application.get_controller().set_active_services()
    # We have to create the .projectrc twice
    # One generic with main options and another here
    # when services are available to set specific configurations
    if create_projectrc:
        Application.get_controller().create_projectrc()
        Application.get_controller().read_specs(read_extended=True)
        Application.get_controller().make_env()

    # Application.get_controller().check_placeholders()
    log.info("Project initialized")
