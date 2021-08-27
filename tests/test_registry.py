"""
This module will test the registry service
"""
import random
import time

from controller import SWARM_MODE, colors
from tests import Capture, create_project, exec_command


def test_docker_registry(capfd: Capture) -> None:

    if not SWARM_MODE:
        return None

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
        # services=["rabbit", "redis"],
    )

    exec_command(
        capfd,
        "-e HEALTHCHECK_INTERVAL=1s -e SWARM_MANAGER_ADDRESS=127.0.0.1 init",
        "Initializing Swarm with manager IP 127.0.0.1",
        "Swarm is now initialized",
        "Project initialized",
    )

    exec_command(
        capfd,
        "pull backend",
        "Registry 127.0.0.1:5000 not reachable. "
        f"You can start it with {colors.RED}rapydo run registry",
    )

    exec_command(
        capfd,
        "build backend",
        "Registry 127.0.0.1:5000 not reachable. "
        f"You can start it with {colors.RED}rapydo run registry",
    )

    exec_command(
        capfd,
        "start backend",
        "Registry 127.0.0.1:5000 not reachable. "
        f"You can start it with {colors.RED}rapydo run registry",
    )

    exec_command(
        capfd,
        "images",
        "Registry 127.0.0.1:5000 not reachable. "
        f"You can start it with {colors.RED}rapydo run registry",
    )

    exec_command(
        capfd,
        "registry",
        "Registry command is replaced by rapydo run registry",
    )

    exec_command(
        capfd,
        "run registry",
        "Creating",
        "_registry_run",
    )

    time.sleep(1)

    exec_command(
        capfd,
        "images",
        "This registry contains no images",
    )

    exec_command(
        capfd,
        "pull backend",
        "Base images pulled from docker hub and pushed into the local registry",
    )

    exec_command(
        capfd,
        "images",
        "This registry contains 1 image(s):",
        "rapydo/backend",
    )

    exec_command(
        capfd,
        "run registry",
        "The registry is already running at 127.0.0.1:5000",
    )
