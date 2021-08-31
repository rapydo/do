"""
This module will test the start command
"""

import random
import shutil
from pathlib import Path

from controller import SWARM_MODE, colors
from tests import (
    Capture,
    create_project,
    exec_command,
    init_project,
    pull_images,
    start_registry,
)


def test_all(capfd: Capture) -> None:

    rand = random.SystemRandom()

    auth = rand.choice(
        (
            "postgres",
            "mysql",
            "neo4j",
            "mongo",
        )
    )

    project_name = "first"
    create_project(
        capfd=capfd,
        name=project_name,
        auth=auth,
        frontend="angular",
        services=["neo4j"],
    )

    init_project(capfd, "-e HEALTHCHECK_INTERVAL=1s")

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

    if SWARM_MODE:

        # Deploy a sub-stack
        exec_command(
            capfd,
            "start backend",
            "Stack started",
        )

        # Once started a stack in swarm mode, it's not possible
        # to re-deploy another stack
        exec_command(
            capfd,
            "start",
            "A stack is already running",
            f"Stop it with {colors.RED}rapydo remove{colors.RESET} "
            "if you want to start a new stack",
        )

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

        # Once started a stack in swarm mode, it's not possible
        # to re-deploy another stack
        exec_command(
            capfd,
            "start backend",
            "A stack is already running",
            f"Stop it with {colors.RED}rapydo remove{colors.RESET} "
            "if you want to start a new stack",
        )

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
        exec_command(
            capfd,
            "start",
            "Stack started",
        )

        exec_command(
            capfd,
            "start",
            "A stack is already running.",
        )
