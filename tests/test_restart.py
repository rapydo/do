"""
This module will test the restart command
"""
from controller import SWARM_MODE
from tests import (
    Capture,
    create_project,
    exec_command,
    init_project,
    pull_images,
    start_project,
)


def test_all(capfd: Capture) -> None:

    create_project(
        capfd=capfd,
        name="first",
        auth="postgres",
        frontend="no",
    )
    init_project(capfd)
    pull_images(capfd)

    if SWARM_MODE:
        exec_command(
            capfd, "restart", "Stack swarm is not running, deploy it with rapydo start"
        )

    start_project(capfd)

    exec_command(
        capfd,
        "restart",
        "Stack restarted",
    )

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
            "Restarting services:",
            "Updating service swarm_backend",
            "Stack restarted",
        )

    exec_command(
        capfd,
        "remove --all backend",
        "Stack removed",
    )
