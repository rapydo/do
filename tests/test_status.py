"""
This module will test the status command
"""
import time

from controller import SWARM_MODE
from tests import (
    Capture,
    create_project,
    exec_command,
    init_project,
    pull_images,
    start_project,
    start_registry,
)


def test_all(capfd: Capture) -> None:

    create_project(
        capfd=capfd,
        name="first",
        auth="postgres",
        frontend="no",
    )
    init_project(capfd)
    if SWARM_MODE:
        start_registry(capfd)
    pull_images(capfd)

    if SWARM_MODE:
        exec_command(
            capfd,
            "status",
            "====== Nodes ======",
            "Manager",
            "Ready+Active",
            "No service is running",
        )
    else:
        exec_command(
            capfd,
            "status",
            "No container is running",
        )

    start_project(capfd)

    if SWARM_MODE:
        time.sleep(1)

        exec_command(
            capfd,
            "status",
            "====== Nodes ======",
            "Manager",
            "Ready+Active",
            "====== Services ======",
            "first_backend",
            "first_postgres",
            " [1]",
            "starting",
        )

        init_project(capfd, "-e HEALTHCHECK_INTERVAL=1s", "--force")

        exec_command(
            capfd,
            "restart --force",
            "Stack restarted",
        )

        time.sleep(2)

        exec_command(
            capfd,
            "status",
            "running",
        )

    else:
        exec_command(
            capfd,
            "status",
            "first_backend_1",
        )
