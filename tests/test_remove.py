"""
This module will test the remove command
"""

from tests import (
    Capture,
    create_project,
    exec_command,
    init_project,
    pull_images,
    start_project,
)


def test_remove(capfd: Capture) -> None:

    create_project(
        capfd=capfd,
        name="first",
        auth="postgres",
        frontend="no",
    )
    init_project(capfd)
    pull_images(capfd)
    start_project(capfd)

    exec_command(
        capfd,
        "remove --all backend",
        "Stack removed",
    )

    exec_command(
        capfd,
        "remove",
        "Stack removed",
    )

    exec_command(
        capfd, "remove --all", "--all option not implemented yet", "Stack removed"
    )
