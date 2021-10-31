"""
This module will test the restart command
"""
import time

from controller import SWARM_MODE, colors
from controller.deploy.docker import Docker
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

    if SWARM_MODE:
        exec_command(
            capfd,
            "restart",
            f"Your stack is not running, deploy it with {colors.RED}rapydo start",
        )

    start_project(capfd)

    docker = Docker()
    container_name = docker.get_container("backend")
    assert container_name is not None

    container = docker.client.container.inspect(container_name)
    start_date1 = container.state.started_at

    exec_command(
        capfd,
        "restart",
        "Stack restarted",
    )

    container_name = docker.get_container("backend")
    assert container_name is not None

    container = docker.client.container.inspect(container_name)
    start_date2 = container.state.started_at

    # The service is not restarted because its definition is unchanged
    assert start_date1 == start_date2

    if SWARM_MODE:
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

    container_name = docker.get_container("backend")
    # Just wait a bit to prevent errors on non existing containers
    if SWARM_MODE:
        time.sleep(1)

    assert container_name is not None

    container = docker.client.container.inspect(container_name)
    start_date3 = container.state.started_at

    assert start_date2 != start_date3
