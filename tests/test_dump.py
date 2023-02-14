"""
This module will test the dump command
"""

from faker import Faker

from tests import (
    Capture,
    create_project,
    exec_command,
    execute_outside,
    init_project,
    random_project_name,
)


def test_dump(capfd: Capture, faker: Faker) -> None:
    execute_outside(capfd, "dump")

    create_project(
        capfd=capfd,
        name=random_project_name(faker),
        auth="postgres",
        frontend="no",
    )
    init_project(capfd)

    exec_command(
        capfd,
        "dump",
        "Config dump: docker-compose.yml",
    )
