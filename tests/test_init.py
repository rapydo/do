"""
This module will test the init command.
Other module that will initialize projects will consider the init command fully working
"""
import os
from pathlib import Path

from faker import Faker

from controller import __version__
from controller.app import Configuration
from controller.deploy.docker import Docker
from controller.utilities import git, system
from tests import (
    Capture,
    TemporaryRemovePath,
    create_project,
    exec_command,
    execute_outside,
    init_project,
    random_project_name,
)


def test_init(capfd: Capture, faker: Faker) -> None:
    execute_outside(capfd, "init")
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

    if Configuration.swarm_mode:
        exec_command(
            capfd,
            "-e HEALTHCHECK_INTERVAL=1s -e SWARM_MANAGER_ADDRESS=127.0.0.1 init",
            "docker compose is installed",
            "Initializing Swarm with manager IP 127.0.0.1",
            "Swarm is now initialized",
            "Project initialized",
        )

        docker = Docker()
        docker.client.swarm.leave(force=True)
        local_ip = system.get_local_ip(production=False)
        exec_command(
            capfd,
            "-e HEALTHCHECK_INTERVAL=1s -e SWARM_MANAGER_ADDRESS= init",
            "docker compose is installed",
            "Swarm is now initialized",
            f"Initializing Swarm with manager IP {local_ip}",
            "Project initialized",
        )

        exec_command(
            capfd,
            "init",
            "Swarm is already initialized",
            "Project initialized",
        )

    else:
        init_project(capfd)

    repo = git.get_repo("submodules/http-api")
    git.switch_branch(repo, "0.7.6")

    exec_command(
        capfd,
        "init",
        f"Switched http-api branch from 0.7.6 to {__version__}",
        f"do already set on branch {__version__}",
    )

    os.rename("submodules", "submodules.bak")
    os.mkdir("submodules")

    # This is to re-fill the submodules folder,
    # these folder will be removed by the next init
    exec_command(capfd, "init", "Project initialized")

    modules_path = Path("submodules.bak").resolve()

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
