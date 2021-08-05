"""
This module will test the registry service
"""
import random

from tests import Capture, create_project


def test_swarm_multi_host(capfd: Capture) -> None:

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
        frontend="no",
        services=["rabbit", "redis"],
    )

    # This is a temporary command and will probably be merged
    #  with interfaces and volatile commands in a near future
