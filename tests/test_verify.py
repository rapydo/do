"""
This module will test the verify command
"""
from tests import create_project, exec_command, random_project_name


def test_verify(capfd, fake):

    create_project(
        capfd=capfd,
        name=random_project_name(fake),
        auth="postgres",
        frontend="angular",
        services=["neo4j"],
        init=True,
        pull=True,
        start=False,
    )

    exec_command(
        capfd, "verify --no-tty sqlalchemy", "No container found for backend_1"
    )

    exec_command(
        capfd,
        "start",
        "docker-compose command: 'up'",
        "Stack started",
    )

    exec_command(capfd, "verify --no-tty invalid", "Service invalid not detected")
    exec_command(capfd, "verify --no-tty redis", "Service redis not detected")
    exec_command(capfd, "verify --no-tty sqlalchemy", "Service sqlalchemy is reachable")
    exec_command(capfd, "verify --no-tty neo4j", "Service neo4j is reachable")

    exec_command(capfd, "remove --all", "Stack removed")
