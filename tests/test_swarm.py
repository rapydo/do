"""
This module will test the swarm mode
"""

import os
import random
import time

from controller import __version__
from controller.swarm import Swarm
from tests import Capture, create_project, exec_command


def test_swarm(capfd: Capture) -> None:
    os.environ["SWARM_MODE"] = "1"

    rand = random.SystemRandom()

    auth = rand.choice(
        (
            "postgres",
            "mysql",
            "neo4j",
            "mongo",
        )
    )

    create_project(
        capfd=capfd,
        name="swarm",
        auth=auth,
        frontend="angular",
        init=False,
        pull=True,
        start=False,
    )

    exec_command(
        capfd,
        "init",
        "Compose configuration dumped on docker-compose.yml",
        "Swarm is now initialized",
        "Project initialized",
    )

    exec_command(
        capfd,
        "init",
        "Compose configuration dumped on docker-compose.yml",
        "Swarm is already initialized",
        "Project initialized",
    )

    # Skipping main because we are on a fake git repository
    exec_command(
        capfd,
        "check -i main",
        "Compose configuration dumped on docker-compose.yml",
        "Swarm is correctly initialized",
        "Checks completed",
    )

    # Skipping main because we are on a fake git repository
    exec_command(
        capfd,
        "check -i main",
        "Compose configuration dumped on docker-compose.yml",
        "Swarm is correctly initialized",
        "Checks completed",
    )

    swarm = Swarm()
    swarm.leave()

    exec_command(
        capfd,
        "check -i main",
        "Compose configuration dumped on docker-compose.yml",
        "Swarm is not initialized, please execute rapydo init",
    )
    exec_command(
        capfd,
        "init",
        "Compose configuration dumped on docker-compose.yml",
        "Swarm is now initialized",
        "Project initialized",
    )
    exec_command(
        capfd,
        "check -i main",
        "Swarm is correctly initialized",
        "Checks completed",
    )

    exec_command(
        capfd,
        "start --force",
        "Force flag is not yet implemented",
        "Stack started",
    )

    # exec_command(
    #     capfd,
    #     "status",
    #     "====== Nodes ======",
    #     "Manager",
    #     "Ready+Active",
    #     "====== Services ======",
    #     f"swarm_backend (rapydo/backend:{__version__})",
    #     f"swarm_frontend (rapydo/angular:{__version__})",
    #     " \\_ [1]",
    #     "preparing",
    # )

    time.sleep(5)

    exec_command(
        capfd,
        "status",
        "====== Nodes ======",
        "Manager",
        "Ready+Active",
        "====== Services ======",
        f"swarm_backend (rapydo/backend:{__version__})",
        f"swarm_frontend (rapydo/angular:{__version__})",
        " \\_ [1]",
        "running",
    )

    exec_command(
        capfd, "remove --all", "rm_all flag is not implemented yet", "Not implemented"
    )

    exec_command(
        capfd, "remove", "rm_networks is currently always enabled", "Stack removed"
    )

    exec_command(
        capfd,
        "status",
        "====== Nodes ======",
        "Manager",
        "Ready+Active",
        "No service is running",
    )
