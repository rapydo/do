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

    init_project(capfd, " -e HEALTHCHECK_INTERVAL=1s")
    start_registry(capfd)

    exec_command(
        capfd,
        "password backend",
        "Please specify one between --random and --password options",
    )


# To be moved in test_password_mongo.py ... when it will be created
# password mongo is still unsupported
def test_mongodb_invalid_characters(capfd: Capture, faker: Faker) -> None:

    create_project(
        capfd=capfd,
        name=random_project_name(faker),
        auth="postgres",
        frontend="no",
        services=["mongo"],
        extra="--env MONGO_PASSWORD=invalid#password",
    )

    informative = "Some special characters, including #, are not allowed "
    informative += "because make some clients to fail to connect"

    exec_command(
        capfd,
        "init --force",
        "Not allowed characters found in MONGO_PASSWORD.",
        informative,
    )
