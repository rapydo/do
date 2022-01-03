"""
This module will test the password command and the passwords management
"""
import time
from datetime import datetime

from faker import Faker

from controller import colors
from controller.app import Configuration
from tests import (
    Capture,
    create_project,
    exec_command,
    get_container_start_date,
    get_variable_from_projectrc,
    init_project,
    pull_images,
    random_project_name,
    service_verify,
    start_project,
    start_registry,
)


def test_password_redis(capfd: Capture, faker: Faker) -> None:

    project_name = random_project_name(faker)
    create_project(
        capfd=capfd,
        name=project_name,
        auth="no",
        frontend="no",
        services=["redis"],
    )

    init_project(capfd, "-e API_AUTOSTART=1")
    start_registry(capfd)

    today = datetime.now().strftime("%Y-%m-%d")

    exec_command(
        capfd,
        "password",
        f"redis      REDIS_PASSWORD         {colors.RED}N/A",
    )

    redis_pass1 = get_variable_from_projectrc("REDIS_PASSWORD")
    exec_command(
        capfd,
        "password redis --random",
        "redis was not running, restart is not needed",
        "The password of redis has been changed. ",
        "Please find the new password into your .projectrc file as "
        "REDIS_PASSWORD variable",
    )
    redis_pass2 = get_variable_from_projectrc("REDIS_PASSWORD")
    assert redis_pass1 != redis_pass2

    exec_command(
        capfd,
        "password",
        f"redis      REDIS_PASSWORD         {colors.GREEN}{today}",
    )

    pull_images(capfd)
    start_project(capfd)

    # DEBUG CODE
    if Configuration.swarm_mode:
        # Added after the upgrade from redis 6.2.5 to 6.2.6
        # 2 minutes !?
        time.sleep(120)
        exec_command(capfd, "logs redis")

    service_verify(capfd, "redis")

    backend_start_date = get_container_start_date(capfd, "backend")
    redis_start_date = get_container_start_date(capfd, "redis")

    exec_command(
        capfd,
        "password redis --random",
        "redis was running, restarting services...",
        "The password of redis has been changed. ",
        "Please find the new password into your .projectrc file as "
        "REDIS_PASSWORD variable",
    )

    redis_pass3 = get_variable_from_projectrc("REDIS_PASSWORD")
    assert redis_pass2 != redis_pass3

    backend_start_date2 = get_container_start_date(capfd, "backend", wait=True)
    redis_start_date2 = get_container_start_date(capfd, "redis", wait=False)

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
    assert mypassword == get_variable_from_projectrc("REDIS_PASSWORD")

    exec_command(
        capfd,
        "password --show",
        mypassword,
    )

    if Configuration.swarm_mode:
        time.sleep(5)

    service_verify(capfd, "redis")

    # Cleanup the stack for the next test
    exec_command(capfd, "remove", "Stack removed")


def test_redis_invalid_characters(capfd: Capture, faker: Faker) -> None:

    create_project(
        capfd=capfd,
        name=random_project_name(faker),
        auth="no",
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
