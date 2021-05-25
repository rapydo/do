"""
This module will test the swarm mode
"""
import random
import time

from controller.swarm import Swarm
from tests import Capture, create_project, exec_command


def test_swarm(capfd: Capture) -> None:

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
        pull=False,
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
        "pull --quiet",
        "Base images pulled from docker hub",
    )

    exec_command(
        capfd,
        "start --force",
        "Force flag is not yet implemented",
        "Stack started",
    )

    time.sleep(2)

    exec_command(
        capfd,
        "status",
        "====== Nodes ======",
        "Manager",
        "Ready+Active",
        "====== Services ======",
        "swarm_backend (rapydo/backend:",
        "swarm_frontend (rapydo/angular:",
        " [1]",
        "running",
    )

    exec_command(capfd, "scale backend=2", "swarm_backend scaled to 3")

    exec_command(
        capfd,
        "status",
        " [2]",
    )

    exec_command(
        capfd, "-e DEFAULT_SCALE_BACKEND=3 scale backend", "swarm_backend scaled to 3"
    )

    exec_command(
        capfd,
        "status",
        " [3]",
    )

    exec_command(
        capfd,
        "scale backend=x",
        "Invalid number of replicas: x",
    )

    with open(".projectrc", "a") as f:
        f.write("\n      DEFAULT_SCALE_BACKEND: 4\n")

    exec_command(capfd, "scale backend", "swarm_backend scaled to 4")

    exec_command(capfd, "scale backend=0", "swarm_backend scaled to 0")

    exec_command(
        capfd,
        "status",
        "! no task is running",
    )

    exec_command(
        capfd,
        "stop",
        "Stop command is not implemented in Swarm Mode",
        "Stop is in contrast with the Docker Swarm approach",
        "You can remove the stack => rapydo remove",
        "Or you can scale all the services to zero => rapydo scale service=0",
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
