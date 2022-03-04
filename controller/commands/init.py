"""
Initialize the current RAPyDo project
"""
from pathlib import Path

import typer

from controller import DATA_DIR, log, print_and_exit
from controller.app import Application, Configuration
from controller.deploy.docker import Docker
from controller.project import ANGULAR


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

    Application.print_command(
        Application.serialize_parameter(
            "--force", create_projectrc, IF=create_projectrc
        ),
        Application.serialize_parameter(
            "--submodules-path", submodules_path, IF=submodules_path
        ),
    )
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
            print_and_exit("Local path not found: {}", submodules_path)

    Application.git_submodules(from_path=submodules_path)

    Application.get_controller().read_specs(read_extended=True)
    Application.get_controller().make_env()

    # Compose services and variables
    Application.get_controller().get_compose_configuration()
    # We have to create the .projectrc twice
    # One generic with main options and another here
    # when services are available to set specific configurations
    if create_projectrc:
        Application.get_controller().create_projectrc()
        Application.get_controller().read_specs(read_extended=True)
        Application.get_controller().make_env()

    if Configuration.swarm_mode:
        docker = Docker(verify_swarm=False)
        if not docker.swarm.get_token():
            docker.swarm.init()
            log.info("Swarm is now initialized")
        else:
            log.debug("Swarm is already initialized")

    if Configuration.frontend == ANGULAR:
        yarn_lock = DATA_DIR.joinpath(Configuration.project, "frontend", "yarn.lock")
        if yarn_lock.exists():
            yarn_lock.unlink()
            log.info("Yarn lock file deleted")

    log.info("Project initialized")
