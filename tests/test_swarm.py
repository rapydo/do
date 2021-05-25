"""
This module will test the swarm mode
"""

import os
import random
import time

from controller import __version__
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
        init=True,
        pull=False,
        start=False,
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

    time.sleep(10)

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
