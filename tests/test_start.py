"""
This module will test the start command
"""

import shutil
import time
from pathlib import Path

from controller import SWARM_MODE, colors
from controller.deploy.docker import Docker
from tests import (
    Capture,
    create_project,
    exec_command,
    execute_outside,
    init_project,
    pull_images,
    start_registry,
)


def test_all(capfd: Capture) -> None:

    execute_outside(capfd, "start")
    if not SWARM_MODE:
        execute_outside(capfd, "stop")

    project_name = "first"
    create_project(
        capfd=capfd,
        name=project_name,
        auth="neo4j",
        frontend="angular",
    )

    init_project(capfd)

    if SWARM_MODE:
        exec_command(
            capfd,
            "start",
            "Registry 127.0.0.1:5000 not reachable.",
        )

        start_registry(capfd)

    exec_command(
        capfd,
        "start backend invalid",
        "No such service: invalid",
    )

    exec_command(
        capfd,
        "start backend",
        f"image, execute {colors.RED}rapydo pull backend",
    )

    pull_images(capfd)

    docker = Docker()

    if SWARM_MODE:

        # Deploy a sub-stack
        exec_command(
            capfd,
            "start backend",
            "Enabled services: ['backend']",
            "Stack started",
        )

        time.sleep(2)

        # Only backend is expected to be running
        assert docker.get_container("backend", slot=1) is not None
        assert docker.get_container("neo4j", slot=1) is None

        # Once started a stack in swarm mode, it's not possible
        # to re-deploy another stack
        # exec_command(
        #     capfd,
        #     "start",
        #     "A stack is already running",
        #     f"Stop it with {colors.RED}rapydo remove{colors.RESET} "
        #     "if you want to start a new stack",
        # )

        # Deploy an additional sub-stack
        exec_command(
            capfd,
            "start neo4j",
            "Enabled services: ['neo4j']",
            "Stack started",
        )

        time.sleep(2)

        # In swarm mode new stack replaces the previous
        # => Only neo4j is expected to be running
        assert docker.get_container("backend", slot=1) is None
        assert docker.get_container("neo4j", slot=1) is not None

        exec_command(
            capfd,
            "remove",
            "Stack removed",
        )

        # Deploy the full stack
        exec_command(
            capfd,
            "start",
            "Stack started",
        )

        time.sleep(2)

        # Now both backend and neo4j are expected to be running
        assert docker.get_container("backend", slot=1) is not None
        assert docker.get_container("neo4j", slot=1) is not None

        # ############################
        # Verify bind volumes checks #
        # ############################

        exec_command(
            capfd,
            "remove",
            "Stack removed",
        )

        data_folder = Path("data", project_name)
        karma_folder = data_folder.joinpath("karma")

        # Delete data/project_name/karma and it will be recreated
        assert karma_folder.exists()
        shutil.rmtree(karma_folder)
        assert not karma_folder.exists()

        # set the data folder read only
        data_folder.chmod(0o550)

        # The missing folder can't be recreated due to permissions denied
        exec_command(
            capfd,
            "start frontend",
            "A bind folder is missing and can't be automatically created: ",
            f"/data/{project_name}/karma",
        )
        assert not karma_folder.exists()

        # Restore RW permissions
        data_folder.chmod(0o770)

        exec_command(
            capfd,
            "start frontend",
            "A bind folder was missing and was automatically created: ",
            f"/data/{project_name}/karma",
            "Stack started",
        )
        assert karma_folder.exists()
    else:

        # Deploy a sub-stack
        exec_command(
            capfd,
            "start backend",
            "Enabled services: ['backend']",
            "Stack started",
        )

        # Only backend is expected to be running
        assert docker.get_container("backend", slot=1) is not None
        assert docker.get_container("neo4j", slot=1) is None

        # Deploy an additional sub-stack
        exec_command(
            capfd,
            "start neo4j",
            "Enabled services: ['neo4j']",
            "Stack started",
        )

        # In compose mode additional stack are aggregated
        # => both backend and neo4j are expected to be running
        assert docker.get_container("backend", slot=1) is not None
        assert docker.get_container("neo4j", slot=1) is not None

        # exec_command(
        #     capfd,
        #     "start",
        #     "A stack is already running.",
        # )
        exec_command(
            capfd,
            "start",
            "Stack started",
        )
