"""
This module will test the password command and the passwords management
"""
from faker import Faker

from controller import SWARM_MODE, colors
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


def test_password(capfd: Capture, faker: Faker) -> None:
    create_project(
        capfd=capfd,
        name=random_project_name(faker),
        auth="postgres",
        frontend="no",
        services=["neo4j", "mysql", "mongo", "rabbit", "redis", "flower"],
    )

    init_project(capfd)
    if SWARM_MODE:
        start_registry(capfd)

    exec_command(
        capfd,
        "password",
        f"backend     AUTH_DEFAULT_PASSWORD {colors.RED}N/A"
        f"postgres    ALCHEMY_PASSWORD      {colors.RED}N/A",
        f"mariadb     ALCHEMY_PASSWORD      {colors.RED}N/A",
        f"mariadb     MYSQL_ROOT_PASSWORD   {colors.RED}N/A",
        f"mongodb     MONGO_PASSWORD        {colors.RED}N/A",
        f"neo4j       NEO4J_PASSWORD        {colors.RED}N/A",
        f"rabbit      RABBITMQ_PASSWORD     {colors.RED}N/A",
        f"redis       REDIS_PASSWORD        {colors.RED}N/A",
        f"flower      FLOWER_PASSWORD       {colors.RED}N/A",
    )

    # ######################################
    # ###  COMMANDS NOT IMPLEMENTED YET  ###
    # ######################################

    exec_command(
        capfd,
        "password backend",
        "Change password for backend not implemented yet",
    )
    exec_command(
        capfd,
        "password postgres",
        "Change password for postgres not implemented yet",
    )
    exec_command(
        capfd,
        "password mariadb",
        "Change password for mariadb not implemented yet",
    )
    exec_command(
        capfd,
        "password mongodb",
        "Change password for mongodb not implemented yet",
    )
    exec_command(
        capfd,
        "password neo4j",
        "Change password for neo4j not implemented yet",
    )
    exec_command(
        capfd,
        "password rabbit",
        "Change password for rabbit not implemented yet",
    )
    exec_command(
        capfd,
        "password flower",
        "Change password for flower not implemented yet",
    )

    if SWARM_MODE:
        exec_command(
            capfd,
            "password registry",
            "Change password for registry not implemented yet",
        )

    # #############################################
    # ###  COMMANDS REQUIRING RUNNING SERVICES  ###
    # #############################################

    # execute and verify the failure due to non running services

    # #################################################
    # ###  COMMANDS NOT REQUIRING RUNNING SERVICES  ###
    # #################################################

    # execute and verify the success

    pull_images(capfd)
    start_project(capfd)

    # #############################################
    # ###  COMMANDS REQUIRING RUNNING SERVICES  ###
    # #############################################

    # execute and verify the success of EVERYTHING
    # (also commands already tests with no running services)


def test_rabbit_invalid_characters(capfd: Capture, faker: Faker) -> None:

    create_project(
        capfd=capfd,
        name=random_project_name(faker),
        auth="postgres",
        frontend="no",
        services=["rabbit"],
        extra="--env RABBITMQ_PASSWORD=invalid£password",
    )

    informative = "Some special characters, including £ § ” ’, are not allowed "
    informative += "because make RabbitMQ crash at startup"

    exec_command(
        capfd,
        "init --force",
        "Not allowed characters found in RABBITMQ_PASSWORD.",
        informative,
    )


def test_redis_invalid_characters(capfd: Capture, faker: Faker) -> None:

    create_project(
        capfd=capfd,
        name=random_project_name(faker),
        auth="postgres",
        frontend="no",
        services=["redis"],
        extra="--env REDIS_PASSWORD=invalid#password",
    )

    informative = "Some special characters, including #, are not allowed "
    informative += "because make some clients to fail to connect"

    exec_command(
        capfd,
        "init --force",
        "Not allowed characters found in REDIS_PASSWORD.",
        informative,
    )


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
