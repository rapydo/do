"""
This module will test the password command and the passwords management
"""
import time
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
    project_name = random_project_name(faker)
    create_project(
        capfd=capfd,
        name=project_name,
        auth="postgres",
        frontend="no",
        services=["neo4j", "mysql", "mongo", "rabbit", "redis", "flower"],
    )

    init_project(capfd, "-e HEALTHCHECK_INTERVAL=1s")
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

    if SWARM_MODE:
        exec_command(
            capfd,
            "password registry --random",
            "Change password for registry not implemented yet",
        )

    # ########################################################
    # ###  TEST rapydo password WITH SERVICES NOT RUNNING  ###
    # ########################################################

    redis_pass1 = get_password_from_projectrc("REDIS_PASSWORD")
    exec_command(
        capfd,
        "password redis --random",
        "redis was not running, restart is not needed",
        "The password of redis has been changed. ",
        "Please find the new password into your .projectrc file as "
        "REDIS_PASSWORD variable",
    )
    redis_pass2 = get_password_from_projectrc("REDIS_PASSWORD")
    assert redis_pass1 != redis_pass2

    flower_pass1 = get_password_from_projectrc("FLOWER_PASSWORD")
    exec_command(
        capfd,
        "password flower --random",
        "flower was not running, restart is not needed",
        "The password of flower has been changed. ",
        "Please find the new password into your .projectrc file as "
        "FLOWER_PASSWORD variable",
    )
    flower_pass2 = get_password_from_projectrc("FLOWER_PASSWORD")
    assert flower_pass1 != flower_pass2

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
        f"flower      FLOWER_PASSWORD       {colors.GREEN}{today}",
    )

    pull_images(capfd)
    start_project(capfd)

    # ########################################################
    # ###  TEST rapydo password WITH SERVICES     RUNNING  ###
    # ########################################################

    if SWARM_MODE:
        swarm = Swarm()

    def get_start_date(capfd: Capture, service: str, wait: bool = False) -> datetime:

        if SWARM_MODE:
            if wait:
                # This is needed to debug and wait the service rollup to complete
                # Status is both for debug and to delay the get_container
                exec_command(capfd, "status")
                time.sleep(3)

            container_name = swarm.get_container(service, slot=1)
        else:
            container_name = f"{project_name}_{service}_1"

        assert container_name is not None
        return docker.container.inspect(container_name).state.started_at

    #  ############## REDIS ######################
    backend_start_date = get_start_date(capfd, "backend")
    redis_start_date = get_start_date(capfd, "redis")

    exec_command(
        capfd,
        "password redis --random",
        "redis was running, restarting services...",
        "The password of redis has been changed. ",
        "Please find the new password into your .projectrc file as "
        "REDIS_PASSWORD variable",
    )

    redis_pass3 = get_password_from_projectrc("REDIS_PASSWORD")
    assert redis_pass2 != redis_pass3

    backend_start_date2 = get_start_date(capfd, "backend", wait=True)
    redis_start_date2 = get_start_date(capfd, "redis", wait=True)

    # Verify that both backend and redis are restarted
    assert backend_start_date2 != backend_start_date
    assert redis_start_date2 != redis_start_date

    #  ############## FLOWER #####################

    flower_start_date = get_start_date(capfd, "flower", wait=True)

    exec_command(
        capfd,
        "password flower --random",
        "flower was running, restarting services...",
        "The password of flower has been changed. ",
        "Please find the new password into your .projectrc file as "
        "FLOWER_PASSWORD variable",
    )

    flower_pass3 = get_password_from_projectrc("FLOWER_PASSWORD")
    assert flower_pass2 != flower_pass3

    flower_start_date2 = get_start_date(capfd, "flower", wait=True)

    assert flower_start_date2 != flower_start_date

    # ########################################################
    # ###      TEST rapydo password --password OPTION      ###
    # ########################################################

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
