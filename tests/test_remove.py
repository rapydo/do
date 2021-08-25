"""
This module will test the remove command
"""

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


def test_remove(capfd: Capture) -> None:

    create_project(
        capfd=capfd,
        name="rem",
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
            "remove backend",
            "Stack rem is not running, deploy it with rapydo start",
        )
    else:
        exec_command(
            capfd,
            "remove",
            "Stack removed",
        )

    start_project(capfd)

    if SWARM_MODE:
        exec_command(
            capfd,
            "remove backend",
            "swarm_backend scaled to 0",
            "verify: Service converged",
            "Services removed",
        )

        exec_command(
            capfd,
            "restart",
            "Stack restarted",
        )

        exec_command(
            capfd,
            "remove",
            "Stack removed",
        )

    else:

        exec_command(
            capfd,
            "remove",
            "Stack removed",
        )

        exec_command(
            capfd,
            "remove --all backend",
            "Stack removed",
        )

        exec_command(
            capfd, "remove --all", "--all option not implemented yet", "Stack removed"
        )
