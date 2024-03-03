"""
This module will test the password command and the passwords management
"""
from faker import Faker

from tests import (
    Capture,
    create_project,
    exec_command,
    execute_outside,
    init_project,
    random_project_name,
    start_registry,
)


def test_password(capfd: Capture, faker: Faker) -> None:
    execute_outside(capfd, "password")

    project_name = random_project_name(faker)
    create_project(
        capfd=capfd,
        name=project_name,
        auth="postgres",
        frontend="no",
    )

    init_project(capfd)
    start_registry(capfd)

    exec_command(
        capfd,
        "password backend",
        "Please specify one between --random and --password options",
    )
