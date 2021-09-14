"""
This module will test the password command and the passwords management
"""
from datetime import datetime

from faker import Faker
from glom import glom
from python_on_whales import docker

from controller import PROJECTRC, SWARM_MODE, colors
from controller.deploy.swarm import Swarm
from controller.utilities import configuration
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


def get_password_from_projectrc(variable: str) -> str:
    projectrc = configuration.load_yaml_file(file=PROJECTRC, is_optional=False)

    return glom(
        projectrc, f"project_configuration.variables.env.{variable}", default=""
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
        f"backend     AUTH_DEFAULT_PASSWORD {colors.RED}N/A",
        f"postgres    ALCHEMY_PASSWORD      {colors.RED}N/A",
        f"mariadb     ALCHEMY_PASSWORD      {colors.RED}N/A",
        f"mariadb     MYSQL_ROOT_PASSWORD   {colors.RED}N/A",
        f"mongodb     MONGO_PASSWORD        {colors.RED}N/A",
        f"neo4j       NEO4J_PASSWORD        {colors.RED}N/A",
        f"rabbit      RABBITMQ_PASSWORD     {colors.RED}N/A",
        f"redis       REDIS_PASSWORD        {colors.RED}N/A",
        f"flower      FLOWER_PASSWORD       {colors.RED}N/A",
    )

    exec_command(
        capfd,
        "password backend",
        "Please specify one between --random and --password options",
    )
    exec_command(
        capfd,
        "password postgres",
        "Please specify one between --random and --password options",
    )
    exec_command(
        capfd,
        "password mariadb",
        "Please specify one between --random and --password options",
    )
    exec_command(
        capfd,
        "password mongodb",
        "Please specify one between --random and --password options",
    )
    exec_command(
        capfd,
        "password neo4j",
        "Please specify one between --random and --password options",
    )
    exec_command(
        capfd,
        "password rabbit",
        "Please specify one between --random and --password options",
    )
    exec_command(
        capfd,
        "password redis",
        "Please specify one between --random and --password options",
    )
    exec_command(
        capfd,
        "password flower",
        "Please specify one between --random and --password options",
    )

    # ######################################
    # ###  COMMANDS NOT IMPLEMENTED YET  ###
    # ######################################

    exec_command(
        capfd,
        "password backend --random",
        "Change password for backend not implemented yet",
    )
    exec_command(
        capfd,
        "password postgres --random",
        "Change password for postgres not implemented yet",
    )
    exec_command(
        capfd,
        "password mariadb --random",
        "Change password for mariadb not implemented yet",
    )
    exec_command(
        capfd,
        "password mongodb --random",
        "Change password for mongodb not implemented yet",
    )
    exec_command(
        capfd,
        "password neo4j --random",
        "Change password for neo4j not implemented yet",
    )
    exec_command(
        capfd,
        "password rabbit --random",
        "Change password for rabbit not implemented yet",
    )
    exec_command(
        capfd,
        "password flower --random",
        "Change password for flower not implemented yet",
    )

    if SWARM_MODE:
        exec_command(
            capfd,
            "password registry --random",
            "Change password for registry not implemented yet",
        )

    # #############################################
    # ###  COMMANDS REQUIRING RUNNING SERVICES  ###
    # #############################################

    # execute and verify the failure due to non running services

    # #################################################
    # ###  COMMANDS NOT REQUIRING RUNNING SERVICES  ###
    # #################################################

    redis_pass = get_password_from_projectrc("REDIS_PASSWORD")
    exec_command(
        capfd,
        "password redis --random",
        "The password of redis has been changed. ",
        "Please find the new password into your .projectrc file as "
        "REDIS_PASSWORD variable",
    )
    assert redis_pass != get_password_from_projectrc("REDIS_PASSWORD")

    today = datetime.now().strftime("%Y-%m-%d")

    exec_command(
        capfd,
        "password",
        f"backend     AUTH_DEFAULT_PASSWORD {colors.RED}N/A",
        f"postgres    ALCHEMY_PASSWORD      {colors.RED}N/A",
        f"mariadb     ALCHEMY_PASSWORD      {colors.RED}N/A",
        f"mariadb     MYSQL_ROOT_PASSWORD   {colors.RED}N/A",
        f"mongodb     MONGO_PASSWORD        {colors.RED}N/A",
        f"neo4j       NEO4J_PASSWORD        {colors.RED}N/A",
        f"rabbit      RABBITMQ_PASSWORD     {colors.RED}N/A",
        f"redis       REDIS_PASSWORD        {colors.GREEN}{today}",
        f"flower      FLOWER_PASSWORD       {colors.RED}N/A",
    )

    pull_images(capfd)
    start_project(capfd)

    # #############################################
    # ###  COMMANDS REQUIRING RUNNING SERVICES  ###
    # #############################################

    if SWARM_MODE:
        swarm = Swarm()
        backend_name = swarm.get_container("backend", slot=1)
        redis_name = swarm.get_container("redis", slot=1)
    else:
        backend_name = "first_backend_1"
        redis_name = "first_redis_1"
    assert backend_name is not None
    assert redis_name is not None

    backend = docker.container.inspect(backend_name)
    backend_start_date = backend.state.started_at
    redis = docker.container.inspect(redis_name)
    redis_start_date = redis.state.started_at

    # execute and verify the success of EVERYTHING
    # (also commands already tested with not running services)

    exec_command(
        capfd,
        "password redis --random",
        "The password of redis has been changed. ",
        "Please find the new password into your .projectrc file as "
        "REDIS_PASSWORD variable",
    )

    backend = docker.container.inspect(backend_name)
    backend_start_date2 = backend.state.started_at
    redis = docker.container.inspect(redis_name)
    redis_start_date2 = redis.state.started_at

    # Verify that both backend and redis are restarted
    assert backend_start_date2 != backend_start_date
    assert redis_start_date2 != redis_start_date

    exec_command(
        capfd,
        "password",
        f"backend     AUTH_DEFAULT_PASSWORD {colors.RED}N/A",
        f"postgres    ALCHEMY_PASSWORD      {colors.RED}N/A",
        f"mariadb     ALCHEMY_PASSWORD      {colors.RED}N/A",
        f"mariadb     MYSQL_ROOT_PASSWORD   {colors.RED}N/A",
        f"mongodb     MONGO_PASSWORD        {colors.RED}N/A",
        f"neo4j       NEO4J_PASSWORD        {colors.RED}N/A",
        f"rabbit      RABBITMQ_PASSWORD     {colors.RED}N/A",
        f"redis       REDIS_PASSWORD        {colors.GREEN}{today}",
        f"flower      FLOWER_PASSWORD       {colors.RED}N/A",
    )

    # Now verify the --password option

    mypassword = faker.pystr()
    exec_command(
        capfd,
        f"password redis --password {mypassword}",
        "The password of redis has been changed. ",
    )
    assert mypassword == get_password_from_projectrc("REDIS_PASSWORD")

    # Now verify that the password change really works!
    # Not implemented yet


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
