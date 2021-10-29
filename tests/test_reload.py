"""
This module will test the reload command
"""
from faker import Faker

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


def test_base(capfd: Capture, faker: Faker) -> None:

    execute_outside(capfd, "reload")

    create_project(
        capfd=capfd,
        name=random_project_name(faker),
        auth="no",
        frontend="no",
    )
    init_project(capfd)

    exec_command(capfd, "reload", "No service reloaded")
    exec_command(capfd, "reload backend", "No service reloaded")
    exec_command(capfd, "reload invalid", "No such service: invalid")
    exec_command(capfd, "reload backend invalid", "No such service: invalid")

    start_registry(capfd)
    pull_images(capfd)

    start_project(capfd)

    exec_command(capfd, "reload backend", "Reloading Flask...")

    exec_command(capfd, "shell backend -u root 'rm /usr/local/bin/reload'")

    exec_command(
        capfd, "reload backend", "Service backend does not support the reload command"
    )

    exec_command(capfd, "remove", "Stack removed")
