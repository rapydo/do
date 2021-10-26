"""
This module will test the status command
"""
import time

from controller import SWARM_MODE
from tests import (
    Capture,
    create_project,
    exec_command,
    execute_outside,
    init_project,
    pull_images,
    start_project,
    start_registry,
)


def test_all(capfd: Capture) -> None:

    execute_outside(capfd, "status")

    create_project(
        capfd=capfd,
        name="first",
        auth="postgres",
        frontend="no",
    )
    init_project(capfd)
    start_registry(capfd)
    pull_images(capfd)

    if SWARM_MODE:
        exec_command(
            capfd,
            "status",
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
            "Manager",
            "Ready+Active",
            "first_backend",
            "first_postgres",
            " [1]",
            "starting",
        )

        init_project(capfd, "", "--force")

        exec_command(
            capfd,
            "restart --force",
            "Stack restarted",
        )

        time.sleep(4)

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
