"""
This module will test the swarm mode
"""
import random

from tests import Capture, create_project, exec_command


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

    exec_command(
        capfd,
        "-e HEALTHCHECK_INTERVAL=1s init",
        "docker buildx is installed",
        "docker compose is installed",
        # already initialized before the test, in the workflow yml
        "Swarm is already initialized",
        "Project initialized",
    )

    exec_command(
        capfd,
        "pull --quiet",
        "Base images pulled from docker hub",
    )

    # Deploy a sub-stack
    exec_command(
        capfd,
        "-s backend start",
        "Stack started",
    )

    exec_command(
        capfd,
        "status",
        "====== Nodes ======",
        "Manager",
        "Worker" "Ready+Active",
        "====== Services ======",
        "swarm_backend",
        "swarm_frontend",
        " [1]",
        "running",
    )
