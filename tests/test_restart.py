"""
This module will test the restart command
"""
from python_on_whales import docker

from controller import SWARM_MODE, colors
from controller.deploy.swarm import Swarm
from tests import (
    Capture,
    create_project,
    exec_command,
    init_project,
    pull_images,
    start_project,
    start_registry,
)


def test_all(capfd: Capture) -> None:

    create_project(
        capfd=capfd,
        name="first",
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
            "restart",
            f"Stack first is not running, deploy it with {colors.RED}rapydo start",
        )

    start_project(capfd)

    if SWARM_MODE:
        swarm = Swarm()
        container_name = swarm.get_container("backend", slot=1)
    else:
        container_name = "first_backend_1"
    assert container_name is not None

    container = docker.container.inspect(container_name)
    start_date1 = container.state.started_at

    exec_command(
        capfd,
        "restart",
        "Stack restarted",
    )

    if SWARM_MODE:
        swarm = Swarm()
        container_name = swarm.get_container("backend", slot=1)
    else:
        container_name = "first_backend_1"
    assert container_name is not None

    container = docker.container.inspect(container_name)
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

    if SWARM_MODE:
        exec_command(
            capfd,
            "restart --force",
            "Stack restarted",
        )

        if SWARM_MODE:
            swarm = Swarm()
            container_name = swarm.get_container("backend", slot=1)
        else:
            container_name = "first_backend_1"
        assert container_name is not None

        container = docker.container.inspect(container_name)
        start_date3 = container.state.started_at

        assert start_date2 != start_date3
    else:
        exec_command(
            capfd,
            "restart --force",
            "--force not implemented yet",
            "Stack restarted",
        )
