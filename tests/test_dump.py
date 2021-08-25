"""
This module will test the dump command
"""

from faker import Faker

from controller import SWARM_MODE
from tests import (
    Capture,
    create_project,
    exec_command,
    init_project,
    pull_images,
    random_project_name,
)


def test_dump(capfd: Capture, faker: Faker) -> None:

    if SWARM_MODE:
        return None

    create_project(
        capfd=capfd,
        name=random_project_name(faker),
        auth="postgres",
        frontend="no",
    )
    init_project(capfd)
    pull_images(capfd)

    exec_command(
        capfd,
        "dump",
        "Config dump: docker-compose.yml",
    )
