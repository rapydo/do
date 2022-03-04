"""
This module will test the start --force (ex restart) command
"""
from controller.app import Configuration
from tests import (
    Capture,
    create_project,
    exec_command,
    get_container_start_date,
    init_project,
    pull_images,
    start_project,
    start_registry,
)


def test_all(capfd: Capture) -> None:

    exec_command(capfd, "restart", "This command is no longer available")

    create_project(
        capfd=capfd,
        name="first",
        auth="postgres",
        frontend="no",
    )
    init_project(capfd)
    start_registry(capfd)
    pull_images(capfd)
    start_project(capfd)

    start_date1 = get_container_start_date(capfd, "backend")
    exec_command(
        capfd,
        "start",
        "Stack started",
    )

    start_date2 = get_container_start_date(capfd, "backend")

    # The service is not restarted because its definition is unchanged
    assert start_date1 == start_date2

    if Configuration.swarm_mode:
        exec_command(
            capfd,
            "remove backend",
            "first_backend scaled to 0",
            "verify: Service converged",
            "Services removed",
        )

    exec_command(
        capfd,
        "start --force",
        "Stack started",
    )

    start_date3 = get_container_start_date(capfd, "backend")

    assert start_date2 != start_date3
