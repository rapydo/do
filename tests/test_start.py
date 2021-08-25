"""
This module will test the start command
"""

from tests import Capture, create_project, exec_command, init_project, pull_images


def test_all(capfd: Capture) -> None:

    create_project(
        capfd=capfd,
        name="first",
        auth="postgres",
        frontend="angular",
        services=["neo4j"],
    )
    init_project(capfd)

    exec_command(
        capfd,
        "start backend invalid",
        "No such service: invalid",
    )

    exec_command(
        capfd,
        "start backend",
        "image, execute rapydo pull backend",
    )

    pull_images(capfd)

    exec_command(
        capfd,
        "start",
        "Stack started",
    )

    exec_command(
        capfd,
        "start",
        "A stack is already running.",
    )

    exec_command(
        capfd,
        "remove --all backend",
        "Stack removed",
    )
