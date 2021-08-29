"""
This module will test the list command
"""

from faker import Faker

from tests import (
    Capture,
    create_project,
    exec_command,
    init_project,
    random_project_name,
    start_project,
)


def test_all(capfd: Capture, faker: Faker) -> None:

    create_project(
        capfd=capfd,
        name=random_project_name(faker),
        auth="postgres",
        frontend="angular",
        services=["rabbit", "redis"],
        extra="--env CUSTOMVAR1=mycustomvalue --env CUSTOMVAR2=mycustomvalue",
    )
    init_project(capfd)

    # Some tests with list
    exec_command(
        capfd,
        "list",
        "Missing argument 'ELEMENT_TYPE:[env|services|submodules]'.  Choose from:",
    )

    exec_command(
        capfd,
        "list invalid",
        "Invalid value for 'ELEMENT_TYPE:[env|services|submodules]': ",
        "invalid choice: invalid. (choose from env, services, submodules)",
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

    start_project(capfd)

    exec_command(
        capfd,
        "list services",
        "List of active services:",
        "backend",
        "frontend",
        "postgres",
        "rabbit",
        "redis",
        # Probably not running yet, a sleep would be needed
        "running",
    )
