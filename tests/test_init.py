"""
This module will test combinations of init, check and update commands.
Other module that will initialize projects will consider the init command fully working
"""
import os
from pathlib import Path

from faker import Faker

from controller import __version__
from controller.utilities import git
from tests import (
    Capture,
    TemporaryRemovePath,
    create_project,
    exec_command,
    random_project_name,
)


def test_init(capfd: Capture, faker: Faker) -> None:

    create_project(
        capfd=capfd,
        name=random_project_name(faker),
        auth="postgres",
        frontend="no",
    )

    exec_command(
        capfd,
        "check -i main",
        "Repo https://github.com/rapydo/http-api.git missing as submodules/http-api.",
        "You should init your project",
    )

    exec_command(
        capfd,
        "init",
        "Project initialized",
    )

    repo = git.get_repo("submodules/http-api")
    git.switch_branch(repo, "0.7.6")

    exec_command(
        capfd,
        "init",
        f"Switched http-api branch from 0.7.6 to {__version__}",
        f"build-templates already set on branch {__version__}",
        f"do already set on branch {__version__}",
    )

    os.rename("submodules", "submodules.bak")
    os.mkdir("submodules")

    # This is to re-fill the submodules folder,
    # these folder will be removed by the next init
    exec_command(capfd, "init", "Project initialized")

    modules_path = os.path.abspath("submodules.bak")

    with TemporaryRemovePath(Path("submodules.bak/do")):
        exec_command(
            capfd,
            f"init --submodules-path {modules_path}",
            "Submodule do not found in ",
        )
    exec_command(
        capfd,
        f"init --submodules-path {modules_path}",
        "Path submodules/http-api already exists, removing",
        "Project initialized",
    )

    assert os.path.islink("submodules/do")
    assert not os.path.islink("submodules.bak/do")

    # Init again, this time in submodules there are links...
    # and will be removed as well as the folders
    exec_command(
        capfd,
        f"init --submodules-path {modules_path}",
        "Path submodules/http-api already exists, removing",
        "Project initialized",
    )

    exec_command(
        capfd,
        "init --submodules-path invalid/path",
        "Local path not found: invalid/path",
    )

    exec_command(
        capfd,
        "--prod init -f",
        "Created default .projectrc file",
        "Project initialized",
    )

    exec_command(
        capfd,
        "--prod -e MYVAR=MYVAL init -f",
        "Created default .projectrc file",
        "Project initialized",
    )

    with open(".projectrc") as projectrc:
        lines = [line.strip() for line in projectrc.readlines()]
        assert "MYVAR: MYVAL" in lines

    exec_command(capfd, "remove --all", "Stack removed")
