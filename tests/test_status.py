"""
This module will test the status command
"""
from tests import (
    Capture,
    create_project,
    exec_command,
    init_project,
    pull_images,
    signal_handler,
    start_project,
)


def test_all(capfd: Capture) -> None:

    create_project(
        capfd=capfd,
        name="first",
        auth="postgres",
        frontend="angular",
        services=["rabbit", "neo4j"],
    )
    init_project(capfd)
    pull_images(capfd)
    start_project(capfd)

    exec_command(
        capfd,
        "status",
        "first_backend_1",
    )
