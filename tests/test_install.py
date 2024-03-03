"""
This module will test the install command
"""
from pathlib import Path

from faker import Faker

from controller import SUBMODULES_DIR, __version__
from controller.utilities import git
from tests import (
    Capture,
    TemporaryRemovePath,
    create_project,
    exec_command,
    execute_outside,
    init_project,
    random_project_name,
)


def test_install(capfd: Capture, faker: Faker) -> None:
    execute_outside(capfd, "install")

    project = random_project_name(faker)
    create_project(
        capfd=capfd,
        name=project,
        auth="postgres",
        frontend="no",
    )
    init_project(capfd)

    # Initially the controller is installed from pip
    exec_command(
        capfd,
        "update -i main",
        "Controller not updated because it is installed outside this project",
        "Installation path is ",
        ", the current folder is ",
        "All updated",
    )

    with TemporaryRemovePath(SUBMODULES_DIR.joinpath("do")):
        exec_command(
            capfd,
            "install",
            "missing as submodules/do. You should init your project",
        )

    exec_command(capfd, "install 100.0", "Invalid version")

    exec_command(
        capfd, "install docker", "Docker current version:", "Docker installed version:"
    )
    exec_command(capfd, "install compose", "Docker compose is installed")
    exec_command(
        capfd,
        "install buildx",
        "Docker buildx current version:",
        "Docker buildx installed version:",
    )

    exec_command(capfd, "install auto")

    r = git.get_repo("submodules/do")
    git.switch_branch(r, "0.7.6")

    exec_command(
        capfd,
        "install",
        f"Controller repository switched to {__version__}",
    )

    # Here the controller is installed in editable mode from the correct submodules
    # folder (this is exactly the default normal condition)
    exec_command(
        capfd,
        "update -i main",
        # Controller installed from {} and updated
        "Controller installed from ",
        " and updated",
        "All updated",
    )

    # Install the controller from a linked folder to verify that the post-update checks
    # are able to correctly resolve symlinks
    # ###########################################################
    # Copied from test_init_check_update.py from here...
    SUBMODULES_DIR.rename("submodules.bak")
    SUBMODULES_DIR.mkdir()

    # This is to re-fill the submodules folder,
    # these folder will be removed by the next init
    exec_command(capfd, "init", "Project initialized")

    modules_path = Path("submodules.bak").resolve()

    exec_command(
        capfd,
        f"init --submodules-path {modules_path}",
        "Path submodules/http-api already exists, removing",
        "Project initialized",
    )
    # ... to here
    # ###########################################################
    exec_command(
        capfd,
        "update -i main",
        # Controller installed from {} and updated
        "Controller installed from ",
        " and updated",
        "All updated",
    )

    # This test will change the required version
    pconf = f"projects/{project}/project_configuration.yaml"

    # Read and change the content
    fin = open(pconf)
    data = fin.read()
    data = data.replace(f'rapydo: "{__version__}"', 'rapydo: "0.7.6"')
    fin.close()
    # Write the new content
    fin = open(pconf, "w")
    fin.write(data)
    fin.close()

    exec_command(
        capfd,
        "version",
        f"This project is not compatible with rapydo version {__version__}",
        "Please downgrade rapydo to version 0.7.6 or modify this project",
    )

    # Read and change the content
    fin = open(pconf)
    data = fin.read()
    data = data.replace('rapydo: "0.7.6"', 'rapydo: "99.99.99"')
    fin.close()
    # Write the new content
    fin = open(pconf, "w")
    fin.write(data)
    fin.close()

    exec_command(
        capfd,
        "version",
        f"This project is not compatible with rapydo version {__version__}",
        "Please upgrade rapydo to version 99.99.99 or modify this project",
    )

    exec_command(capfd, "install --no-editable 0.8")

    exec_command(capfd, "install --no-editable")

    exec_command(capfd, "install")
