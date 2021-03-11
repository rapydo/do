"""
This module will test the install command
"""
import os

from faker import Faker

from controller import __version__, gitter
from tests import (
    Capture,
    TemporaryRemovePath,
    create_project,
    exec_command,
    random_project_name,
)


def test_install(capfd: Capture, faker: Faker) -> None:

    project = random_project_name(faker)
    create_project(
        capfd=capfd,
        name=project,
        auth="postgres",
        frontend="angular",
        init=True,
        pull=False,
        start=False,
    )

    # Initially the controller is installed from pip
    exec_command(
        capfd,
        "update -i main",
        "Controller not updated because it is installed outside this project",
        "Installation path is ",
        ", the current folder is ",
        "All updated",
    )

    with TemporaryRemovePath("submodules/do"):
        exec_command(
            capfd,
            "install",
            "missing as submodules/do. You should init your project",
        )

    exec_command(capfd, "install 100.0", "Invalid version")

    exec_command(capfd, "install auto")

    r = gitter.get_repo("submodules/do")
    gitter.switch_branch(r, "0.7.6")

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
    os.rename("submodules", "submodules.bak")
    os.mkdir("submodules")

    # This is to re-fill the submodules folder,
    # these folder will be removed by the next init
    exec_command(capfd, "init", "Project initialized")

    modules_path = os.path.abspath("submodules.bak")

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

    exec_command(capfd, "install")

    exec_command(capfd, "install --no-editable")

    # This is the very last command... installing an old version!
    exec_command(capfd, "install --no-editable 0.7.2")

    # This test will change the required version
    pconf = f"projects/{project}/project_configuration.yaml"

    # Read and change the content
    fin = open(pconf)
    data = fin.read()
    data = data.replace(f'rapydo: "{__version__}"', 'rapydo: "0.7.6"')
    fin.close()
    # Write the new content
    fin = open(pconf, "wt")
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
    fin = open(pconf, "wt")
    fin.write(data)
    fin.close()

    exec_command(
        capfd,
        "version",
        f"This project is not compatible with rapydo version {__version__}",
        "Please upgrade rapydo to version 99.99.99 or modify this project",
    )
