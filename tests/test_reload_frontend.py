"""
This module will test the reload command
"""
import time

from faker import Faker

from controller import SWARM_MODE
from tests import (
    Capture,
    create_project,
    exec_command,
    init_project,
    pull_images,
    random_project_name,
    start_project,
    start_registry,
)


def test_reload_dev(capfd: Capture, faker: Faker) -> None:
    create_project(
        capfd=capfd,
        name=random_project_name(faker),
        auth="no",
        frontend="angular",
    )
    init_project(capfd)
    start_registry(capfd)

    pull_images(capfd)

    start_project(capfd)

    # To be improved!!
    time.sleep(10)

    # For each support service verify:
    #   1) a start line in the logs
    #   2) the container is not re-created after the command
    #   3) the start line in the logs is printed again
    #   4) some more deep check based on the service?
    #      For example API is loading a change in the code?
    exec_command(capfd, "reload frontend", "Not implemented yet")


# The frontend exits after the build and can't be reloaded -> no test needed
# def test_reload_prod(capfd: Capture, faker: Faker) -> None:
