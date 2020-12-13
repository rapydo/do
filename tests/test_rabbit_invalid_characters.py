"""
This module will test a verify specific use case where rabbit fails due to some
special characters in the password
"""
from tests import create_project, exec_command, random_project_name


def test_rabbit_invalid_characters(capfd, fake):

    create_project(
        capfd=capfd,
        name=random_project_name(fake),
        auth="postgres",
        frontend="no",
        services=["rabbit"],
        extra="--env RABBITMQ_PASSWORD=invalid£password",
        init=False,
        pull=False,
        start=False,
    )

    informative = "Some special characters, including £ § ” ’, are not allowed "
    informative = "because make RabbitMQ crash at startup"

    exec_command(
        capfd,
        "init --force",
        "Not allowed characters found in RABBITMQ_PASSWORD.",
        informative,
    )
