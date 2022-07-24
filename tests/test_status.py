"""
This module will test the status command
"""
import time

from controller.app import Configuration
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
        name="xx",
        auth="postgres",
        frontend="no",
    )
    init_project(capfd)
    start_registry(capfd)
    pull_images(capfd)

    if Configuration.swarm_mode:
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

    if Configuration.swarm_mode:

        exec_command(
            capfd,
            "status",
            "Manager",
            "Ready+Active",
            "xx_backend_1",
            "xx_postgres_1",
            " [1]",
            # No longer found starting because
            # HEALTHCHECK_INTERVAL is defaulted to 1s during tests
            # "starting",
            "running",
        )

        init_project(capfd, "", "--force")

        exec_command(
            capfd,
            "start --force",
            "Stack started",
        )

        time.sleep(4)

        exec_command(
            capfd,
            "status",
            "running",
        )

        exec_command(
            capfd,
            "status backend",
            "running",
        )

        exec_command(
            capfd,
            "status backend postgres",
            "running",
        )

    else:
        exec_command(
            capfd,
            "status",
            "xx-backend-1",
        )

        exec_command(
            capfd,
            "status backend",
            "xx-backend-1",
        )

        exec_command(
            capfd,
            "status backend postgres",
            "xx-backend-1",
        )
