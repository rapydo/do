"""
This module will test the password command and the passwords management
"""
import time
from datetime import datetime
from typing import Optional

import requests
from faker import Faker
from glom import glom
from python_on_whales import docker

from controller import PROJECTRC, SWARM_MODE, colors
from controller.deploy.swarm import Swarm
from controller.utilities import configuration
from tests import (
    REGISTRY,
    Capture,
    create_project,
    exec_command,
    execute_outside,
    init_project,
    pull_images,
    random_project_name,
    service_verify,
    start_project,
    start_registry,
)


def get_start_date(
    capfd: Capture, service: str, project_name: str, wait: bool = False
) -> datetime:

    # Optional is needed because swarm.get_container returns Optional[str]
    container_name: Optional[str] = None

    if service == REGISTRY:
        container_name = REGISTRY
    elif SWARM_MODE:
        if wait:
            # This is needed to debug and wait the service rollup to complete
            # Status is both for debug and to delay the get_container
            exec_command(capfd, "status")
            time.sleep(4)

        swarm = Swarm()
        container_name = swarm.get_container(service, slot=1)
    else:
        container_name = f"{project_name}_{service}_1"

    assert container_name is not None
    return docker.container.inspect(container_name).state.started_at


def get_password_from_projectrc(variable: str) -> str:
    projectrc = configuration.load_yaml_file(file=PROJECTRC, is_optional=False)

    return glom(
        projectrc, f"project_configuration.variables.env.{variable}", default=""
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


def test_password_registry(capfd: Capture, faker: Faker) -> None:

    if not SWARM_MODE:
        return None

    project_name = random_project_name(faker)
    create_project(
        capfd=capfd,
        name=project_name,
        auth="postgres",
        frontend="no",
    )

    init_project(capfd, " -e HEALTHCHECK_INTERVAL=1s")

    today = datetime.now().strftime("%Y-%m-%d")

    exec_command(
        capfd,
        "password",
        f"registry   REGISTRY_PASSWORD      {colors.RED}N/A",
    )
    registry_pass1 = get_password_from_projectrc("REGISTRY_PASSWORD")

    docker.container.remove(REGISTRY, force=True)

    exec_command(
        capfd,
        "password registry --random",
        "registry was not running, restart is not needed",
        "The password of registry has been changed. ",
        "Please find the new password into your .projectrc file as "
        "REGISTRY_PASSWORD variable",
    )
    registry_pass2 = get_password_from_projectrc("REGISTRY_PASSWORD")
    assert registry_pass1 != registry_pass2

    start_registry(capfd)

    exec_command(
        capfd,
        "password",
        f"registry   REGISTRY_PASSWORD      {colors.GREEN}{today}",
    )

    exec_command(capfd, "images", "This registry contains ")

    registry_start_date = get_start_date(capfd, "registry", project_name, wait=True)

    exec_command(
        capfd,
        "password registry --random",
        "registry was running, restarting services...",
        "The password of registry has been changed. ",
        "Please find the new password into your .projectrc file as "
        "REGISTRY_PASSWORD variable",
    )

    registry_pass3 = get_password_from_projectrc("REGISTRY_PASSWORD")
    assert registry_pass2 != registry_pass3

    registry_start_date2 = get_start_date(capfd, "registry", project_name, wait=True)

    assert registry_start_date2 != registry_start_date

    exec_command(capfd, "images", "This registry contains ")

    exec_command(
        capfd,
        "password",
        f"registry   REGISTRY_PASSWORD      {colors.GREEN}{today}",
    )

    # This is needed otherwise the following tests will be unable to start
    # a new instance of the registry and will fail with registry auth errors
    exec_command(capfd, "remove registry", "Service registry removed")


def test_password_redis(capfd: Capture, faker: Faker) -> None:

    project_name = random_project_name(faker)
    create_project(
        capfd=capfd,
        name=project_name,
        auth="postgres",
        frontend="no",
        services=["redis"],
    )

    init_project(capfd, " -e HEALTHCHECK_INTERVAL=1s -e API_AUTOSTART=1")
    start_registry(capfd)

    today = datetime.now().strftime("%Y-%m-%d")

    exec_command(
        capfd,
        "password",
        f"redis      REDIS_PASSWORD         {colors.RED}N/A",
    )

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

    exec_command(
        capfd,
        "password",
        f"redis      REDIS_PASSWORD         {colors.GREEN}{today}",
    )

    pull_images(capfd)
    start_project(capfd)

    service_verify(capfd, "redis")

    backend_start_date = get_start_date(capfd, "backend", project_name)
    redis_start_date = get_start_date(capfd, "redis", project_name)

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

    backend_start_date2 = get_start_date(capfd, "backend", project_name, wait=True)
    redis_start_date2 = get_start_date(capfd, "redis", project_name, wait=True)

    # Verify that both backend and redis are restarted
    assert backend_start_date2 != backend_start_date
    assert redis_start_date2 != redis_start_date

    service_verify(capfd, "redis")

    exec_command(
        capfd,
        "password",
        f"redis      REDIS_PASSWORD         {colors.GREEN}{today}",
    )

    mypassword = faker.pystr()
    exec_command(
        capfd,
        f"password redis --password {mypassword}",
        "The password of redis has been changed. ",
    )
    assert mypassword == get_password_from_projectrc("REDIS_PASSWORD")

    exec_command(
        capfd,
        "password --show",
        mypassword,
    )

    if SWARM_MODE:
        time.sleep(5)

    service_verify(capfd, "redis")

    # Cleanup the stack for the next test
    exec_command(capfd, "remove", "Stack removed")


def test_password_flower(capfd: Capture, faker: Faker) -> None:

    project_name = random_project_name(faker)
    create_project(
        capfd=capfd,
        name=project_name,
        auth="postgres",
        frontend="no",
        services=["flower"],
    )

    init_project(capfd, " -e HEALTHCHECK_INTERVAL=1s -e API_AUTOSTART=1")
    start_registry(capfd)

    today = datetime.now().strftime("%Y-%m-%d")

    exec_command(
        capfd,
        "password",
        f"flower     FLOWER_PASSWORD        {colors.RED}N/A",
    )

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

    exec_command(
        capfd,
        "password",
        f"flower     FLOWER_PASSWORD        {colors.GREEN}{today}",
    )

    pull_images(capfd)
    start_project(capfd)

    flower_start_date = get_start_date(capfd, "flower", project_name, wait=True)

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

    flower_start_date2 = get_start_date(capfd, "flower", project_name, wait=True)

    assert flower_start_date2 != flower_start_date

    exec_command(
        capfd,
        "password",
        f"flower     FLOWER_PASSWORD        {colors.GREEN}{today}",
    )

    mypassword = faker.pystr()
    exec_command(
        capfd,
        f"password flower --password {mypassword}",
        "The password of flower has been changed. ",
    )
    assert mypassword == get_password_from_projectrc("FLOWER_PASSWORD")

    exec_command(
        capfd,
        "password --show",
        mypassword,
    )

    # Cleanup the stack for the next test
    exec_command(capfd, "remove", "Stack removed")


def test_password_rabbit(capfd: Capture, faker: Faker) -> None:

    project_name = random_project_name(faker)
    create_project(
        capfd=capfd,
        name=project_name,
        auth="postgres",
        frontend="no",
        services=["rabbit"],
    )

    init_project(capfd, " -e HEALTHCHECK_INTERVAL=1s -e API_AUTOSTART=1")
    start_registry(capfd)

    today = datetime.now().strftime("%Y-%m-%d")

    exec_command(
        capfd,
        "password rabbit --random",
        "Can't update rabbit because it is not running. Please start your stack",
    )

    exec_command(
        capfd,
        "password",
        f"rabbit     RABBITMQ_PASSWORD      {colors.RED}N/A",
    )

    pull_images(capfd)
    start_project(capfd)

    service_verify(capfd, "rabbitmq")

    #  ############## RABBIT #####################

    backend_start_date = get_start_date(capfd, "backend", project_name)
    rabbit_start_date = get_start_date(capfd, "rabbit", project_name)
    rabbit_pass1 = get_password_from_projectrc("RABBITMQ_PASSWORD")

    exec_command(
        capfd,
        "password rabbit --random",
        "rabbit was running, restarting services...",
        "The password of rabbit has been changed. ",
        "Please find the new password into your .projectrc file as "
        "RABBITMQ_PASSWORD variable",
    )

    rabbit_pass2 = get_password_from_projectrc("RABBITMQ_PASSWORD")
    assert rabbit_pass1 != rabbit_pass2

    backend_start_date2 = get_start_date(capfd, "backend", project_name, wait=True)
    rabbit_start_date2 = get_start_date(capfd, "rabbit", project_name, wait=True)

    # Verify that both backend and rabbit are restarted
    assert backend_start_date2 != backend_start_date
    assert rabbit_start_date2 != rabbit_start_date

    service_verify(capfd, "rabbitmq")

    exec_command(
        capfd,
        "password",
        f"rabbit     RABBITMQ_PASSWORD      {colors.GREEN}{today}",
    )

    mypassword = faker.pystr()
    exec_command(
        capfd,
        f"password rabbit --password {mypassword}",
        "The password of rabbit has been changed. ",
    )
    assert mypassword == get_password_from_projectrc("RABBITMQ_PASSWORD")

    exec_command(
        capfd,
        "password --show",
        mypassword,
    )

    if SWARM_MODE:
        time.sleep(5)

    service_verify(capfd, "rabbitmq")

    # Cleanup the stack for the next test
    exec_command(capfd, "remove", "Stack removed")


def test_password_postgres(capfd: Capture, faker: Faker) -> None:

    project_name = random_project_name(faker)
    create_project(
        capfd=capfd,
        name=project_name,
        auth="postgres",
        frontend="no",
    )

    init_project(capfd, " -e HEALTHCHECK_INTERVAL=1s -e API_AUTOSTART=1")
    start_registry(capfd)

    today = datetime.now().strftime("%Y-%m-%d")

    exec_command(
        capfd,
        "password postgres --random",
        "Can't update postgres because it is not running. Please start your stack",
    )

    exec_command(
        capfd,
        "password",
        f"postgres   ALCHEMY_PASSWORD       {colors.RED}N/A",
    )

    pull_images(capfd)
    start_project(capfd)

    service_verify(capfd, "sqlalchemy")

    backend_start_date = get_start_date(capfd, "backend", project_name)
    postgres_start_date = get_start_date(capfd, "postgres", project_name)
    postgres_pass1 = get_password_from_projectrc("ALCHEMY_PASSWORD")

    exec_command(
        capfd,
        "password postgres --random",
        "postgres was running, restarting services...",
        "The password of postgres has been changed. ",
        "Please find the new password into your .projectrc file as "
        "ALCHEMY_PASSWORD variable",
    )

    postgres_pass2 = get_password_from_projectrc("ALCHEMY_PASSWORD")
    assert postgres_pass1 != postgres_pass2

    backend_start_date2 = get_start_date(capfd, "backend", project_name, wait=True)
    postgres_start_date2 = get_start_date(capfd, "postgres", project_name, wait=True)

    # Verify that both backend and postgres are restarted
    assert backend_start_date2 != backend_start_date
    assert postgres_start_date2 != postgres_start_date

    service_verify(capfd, "sqlalchemy")

    exec_command(
        capfd,
        "password",
        f"postgres   ALCHEMY_PASSWORD       {colors.GREEN}{today}",
    )

    mypassword = faker.pystr()
    exec_command(
        capfd,
        f"password postgres --password {mypassword}",
        "The password of postgres has been changed. ",
    )
    assert mypassword == get_password_from_projectrc("ALCHEMY_PASSWORD")

    exec_command(
        capfd,
        "password --show",
        mypassword,
    )

    if SWARM_MODE:
        time.sleep(5)

    service_verify(capfd, "sqlalchemy")

    # Cleanup the stack for the next test
    exec_command(capfd, "remove", "Stack removed")


def test_password_mysql(capfd: Capture, faker: Faker) -> None:

    project_name = random_project_name(faker)
    create_project(
        capfd=capfd,
        name=project_name,
        auth="mysql",
        frontend="no",
    )

    init_project(capfd, " -e HEALTHCHECK_INTERVAL=1s -e API_AUTOSTART=1")
    start_registry(capfd)

    today = datetime.now().strftime("%Y-%m-%d")

    exec_command(
        capfd,
        "password mariadb --random",
        "Can't update mariadb because it is not running. Please start your stack",
    )

    exec_command(
        capfd,
        "password",
        f"mariadb    ALCHEMY_PASSWORD       {colors.RED}N/A",
        # f"mariadb    MYSQL_ROOT_PASSWORD    {colors.RED}N/A",
    )

    pull_images(capfd)
    start_project(capfd)

    service_verify(capfd, "sqlalchemy")

    backend_start_date = get_start_date(capfd, "backend", project_name)
    mariadb_start_date = get_start_date(capfd, "mariadb", project_name)
    mariadb_pass1 = get_password_from_projectrc("ALCHEMY_PASSWORD")

    exec_command(
        capfd,
        "password mariadb --random",
        "mariadb was running, restarting services...",
        "The password of mariadb has been changed. ",
        "Please find the new password into your .projectrc file as "
        "ALCHEMY_PASSWORD variable",
    )

    mariadb_pass2 = get_password_from_projectrc("ALCHEMY_PASSWORD")
    assert mariadb_pass1 != mariadb_pass2

    backend_start_date2 = get_start_date(capfd, "backend", project_name, wait=True)
    mariadb_start_date2 = get_start_date(capfd, "mariadb", project_name, wait=True)

    # Verify that both backend and mariadb are restarted
    assert backend_start_date2 != backend_start_date
    assert mariadb_start_date2 != mariadb_start_date

    service_verify(capfd, "sqlalchemy")

    exec_command(
        capfd,
        "password",
        f"mariadb    ALCHEMY_PASSWORD       {colors.GREEN}{today}",
        # f"mariadb    MYSQL_ROOT_PASSWORD    {colors.GREEN}{today}",
    )

    mypassword = faker.pystr()
    exec_command(
        capfd,
        f"password mariadb --password {mypassword}",
        "The password of mariadb has been changed. ",
    )
    assert mypassword == get_password_from_projectrc("ALCHEMY_PASSWORD")

    exec_command(
        capfd,
        "password --show",
        mypassword,
    )

    if SWARM_MODE:
        time.sleep(5)

    service_verify(capfd, "sqlalchemy")

    # Cleanup the stack for the next test
    exec_command(capfd, "remove", "Stack removed")


def test_password_neo4j(capfd: Capture, faker: Faker) -> None:

    project_name = random_project_name(faker)
    create_project(
        capfd=capfd,
        name=project_name,
        auth="neo4j",
        frontend="no",
    )

    init_project(capfd, " -e HEALTHCHECK_INTERVAL=1s -e API_AUTOSTART=1")
    start_registry(capfd)

    today = datetime.now().strftime("%Y-%m-%d")

    exec_command(
        capfd,
        "password neo4j --random",
        "Can't update neo4j because it is not running. Please start your stack",
    )

    exec_command(
        capfd,
        "password",
        f"neo4j      NEO4J_PASSWORD         {colors.RED}N/A",
    )

    pull_images(capfd)
    start_project(capfd)

    service_verify(capfd, "neo4j")

    backend_start_date = get_start_date(capfd, "backend", project_name)
    neo4j_start_date = get_start_date(capfd, "neo4j", project_name)
    neo4j_pass1 = get_password_from_projectrc("NEO4J_PASSWORD")

    exec_command(
        capfd,
        "password neo4j --random",
        "neo4j was running, restarting services...",
        "The password of neo4j has been changed. ",
        "Please find the new password into your .projectrc file as "
        "NEO4J_PASSWORD variable",
    )

    neo4j_pass2 = get_password_from_projectrc("NEO4J_PASSWORD")
    assert neo4j_pass1 != neo4j_pass2

    backend_start_date2 = get_start_date(capfd, "backend", project_name, wait=True)
    neo4j_start_date2 = get_start_date(capfd, "neo4j", project_name, wait=True)

    # Verify that both backend and neo4j are restarted
    assert backend_start_date2 != backend_start_date
    assert neo4j_start_date2 != neo4j_start_date

    service_verify(capfd, "neo4j")

    exec_command(
        capfd,
        "password",
        f"neo4j      NEO4J_PASSWORD         {colors.GREEN}{today}",
    )

    mypassword = faker.pystr()
    exec_command(
        capfd,
        f"password neo4j --password {mypassword}",
        "The password of neo4j has been changed. ",
    )
    assert mypassword == get_password_from_projectrc("NEO4J_PASSWORD")

    exec_command(
        capfd,
        "password --show",
        mypassword,
    )

    if SWARM_MODE:
        time.sleep(5)

    service_verify(capfd, "neo4j")

    # Cleanup the stack for the next test
    exec_command(capfd, "remove", "Stack removed")


def test_password_backend(capfd: Capture, faker: Faker) -> None:

    project_name = random_project_name(faker)
    create_project(
        capfd=capfd,
        name=project_name,
        auth="postgres",
        frontend="no",
    )

    init_project(capfd, " -e HEALTHCHECK_INTERVAL=1s -e API_AUTOSTART=1")
    start_registry(capfd)

    today = datetime.now().strftime("%Y-%m-%d")

    exec_command(
        capfd,
        "password backend --random",
        "Can't update backend because it is not running. Please start your stack",
    )

    exec_command(
        capfd,
        "password",
        f"backend    AUTH_DEFAULT_PASSWORD  {colors.RED}N/A",
    )

    pull_images(capfd)
    start_project(capfd)

    exec_command(capfd, "logs backend --tail 10")
    time.sleep(2)
    r = requests.post(
        "http://localhost:8080/auth/login",
        data={
            "username": get_password_from_projectrc("AUTH_DEFAULT_USERNAME"),
            "password": get_password_from_projectrc("AUTH_DEFAULT_PASSWORD"),
        },
    )
    exec_command(capfd, "logs backend --tail 10")
    assert r.status_code == 200

    backend_start_date = get_start_date(capfd, "backend", project_name)
    backend_pass1 = get_password_from_projectrc("AUTH_DEFAULT_PASSWORD")

    exec_command(
        capfd,
        "password backend --random",
        "backend was running, restarting services...",
        "The password of backend has been changed. ",
        "Please find the new password into your .projectrc file as "
        "AUTH_DEFAULT_PASSWORD variable",
    )

    backend_pass2 = get_password_from_projectrc("AUTH_DEFAULT_PASSWORD")
    assert backend_pass1 != backend_pass2

    backend_start_date2 = get_start_date(capfd, "backend", project_name, wait=True)

    # Verify that backend is restarted
    assert backend_start_date2 != backend_start_date

    exec_command(capfd, "logs backend --tail 10")
    time.sleep(5)
    r = requests.post(
        "http://localhost:8080/auth/login",
        data={
            "username": get_password_from_projectrc("AUTH_DEFAULT_USERNAME"),
            "password": get_password_from_projectrc("AUTH_DEFAULT_PASSWORD"),
        },
    )
    exec_command(capfd, "logs backend --tail 10")
    assert r.status_code == 200

    exec_command(
        capfd,
        "password",
        f"backend    AUTH_DEFAULT_PASSWORD  {colors.GREEN}{today}",
    )

    mypassword = faker.pystr()
    exec_command(
        capfd,
        f"password backend --password {mypassword}",
        "The password of backend has been changed. ",
    )
    assert mypassword == get_password_from_projectrc("AUTH_DEFAULT_PASSWORD")

    exec_command(
        capfd,
        "password --show",
        mypassword,
    )

    exec_command(capfd, "logs backend --tail 10")
    time.sleep(5)
    r = requests.post(
        "http://localhost:8080/auth/login",
        data={
            "username": get_password_from_projectrc("AUTH_DEFAULT_USERNAME"),
            "password": get_password_from_projectrc("AUTH_DEFAULT_PASSWORD"),
        },
    )
    exec_command(capfd, "logs backend --tail 10")
    assert r.status_code == 200

    # Cleanup the stack for the next test
    exec_command(capfd, "remove", "Stack removed")


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
