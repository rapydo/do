"""
This module will test the list command
"""

import time

from faker import Faker

from controller import SWARM_MODE
from tests import (
    Capture,
    create_project,
    exec_command,
    execute_outside,
    init_project,
    pull_images,
    random_project_name,
    start_project,
    start_registry,
)


def test_all(capfd: Capture, faker: Faker) -> None:

    execute_outside(capfd, "list env")
    create_project(
        capfd=capfd,
        name=random_project_name(faker),
        auth="postgres",
        frontend="angular",
        services=["rabbit", "redis"],
        extra="--env CUSTOMVAR1=mycustomvalue --env CUSTOMVAR2=mycustomvalue",
    )
    init_project(capfd, "-e HEALTHCHECK_INTERVAL=1s")

    # Some tests with list
    exec_command(
        capfd,
        "list",
        "Missing argument 'ELEMENT_TYPE:{env|services|submodules}'. Choose from:",
    )

    exec_command(
        capfd,
        "list invalid",
        "Invalid value for",
        "'invalid' is not one of 'env', 'services', 'submodules'",
    )

    exec_command(
        capfd,
        "list env",
        "List env variables:",
        "ACTIVATE_ALCHEMY",
        "CUSTOMVAR1",
        "CUSTOMVAR2",
        "mycustomvalue",
    )
    exec_command(
        capfd,
        "list submodules",
        "List of submodules:",
    )

    exec_command(
        capfd,
        "list services",
        "List of active services:",
        "backend",
        "frontend",
        "postgres",
        "rabbit",
        "redis",
        "N/A",
    )

    if SWARM_MODE:
        start_registry(capfd)

    pull_images(capfd)

    start_project(capfd)

    time.sleep(2)

    exec_command(
        capfd,
        "list services",
        "List of active services:",
        "backend",
        "frontend",
        "postgres",
        "rabbit",
        "redis",
        "running",
    )
