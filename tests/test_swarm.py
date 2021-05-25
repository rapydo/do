"""
This module will test the swarm mode
"""

import os
import random

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

    exec_command(
        capfd, "remove --all", "rm_all flag is not implemented yet", "Not implemented"
    )

    exec_command(
        capfd, "remove", "rm_networks is currently always enabled", "Stack removed"
    )
