"""
This module will test the restart command
"""
from controller import colors
from controller.app import Configuration
from tests import (
    Capture,
    create_project,
    exec_command,
    execute_outside,
    get_container_start_date,
    init_project,
    pull_images,
    start_project,
    start_registry,
)


def test_all(capfd: Capture) -> None:

    execute_outside(capfd, "restart")

    create_project(
        capfd=capfd,
        name="first",
        auth="postgres",
        frontend="no",
    )
    init_project(capfd)
    start_registry(capfd)
    pull_images(capfd)

    if Configuration.swarm_mode:
        exec_command(
            capfd,
            "restart",
            f"Your stack is not running, deploy it with {colors.RED}rapydo start",
        )

    start_project(capfd)

    start_date1 = get_container_start_date(capfd, "backend")
    exec_command(
        capfd,
        "restart",
        "Stack restarted",
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
            "restart",
            "Restarting services:",
            "Updating service first_backend",
            "Stack restarted",
        )

    exec_command(
        capfd,
        "restart --force",
        "Stack restarted",
    )

    start_date3 = get_container_start_date(capfd, "backend")

    assert start_date2 != start_date3
