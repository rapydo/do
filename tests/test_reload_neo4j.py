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
    random_project_name,
    start_registry,
)


def test_reload_neo4j(capfd: Capture, faker: Faker) -> None:
    create_project(
        capfd=capfd,
        name=random_project_name(faker),
        auth="neo4j",
        frontend="no",
    )
    init_project(capfd)
    start_registry(capfd)

    exec_command(
        capfd,
        "pull --quiet neo4j",
        "Base images pulled from docker hub",
    )

    exec_command(
        capfd,
        "start neo4j",
        "Stack started",
    )
    if SWARM_MODE:
        time.sleep(10)
    else:
        time.sleep(5)

    # For each support service verify:
    #   1) a start line in the logs
    #   2) the container is not re-created after the command
    #   3) the start line in the logs is printed again
    #   4) some more deep check based on the service?
    #      For example API is loading a change in the code?
    exec_command(capfd, "reload neo4j", "Not implemented yet")

    exec_command(
        capfd,
        "--prod init -f",
        "Created default .projectrc file",
        "Project initialized",
    )

    exec_command(
        capfd,
        "--prod start neo4j",
        "Stack started",
    )

    if SWARM_MODE:
        time.sleep(15)
    else:
        time.sleep(10)

    exec_command(capfd, "reload neo4j", "Not implemented yet")
