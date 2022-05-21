"""
This module will test the password command and the passwords management
"""
import time
from datetime import datetime, timedelta

from faker import Faker
from freezegun import freeze_time

from controller import colors
from controller.app import Configuration
from controller.commands.password import PASSWORD_EXPIRATION
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


def test_password_rabbit(capfd: Capture, faker: Faker) -> None:

    project_name = random_project_name(faker)
    create_project(
        capfd=capfd,
        name=project_name,
        auth="no",
        frontend="no",
        services=["rabbit"],
    )

    init_project(capfd, "-e API_AUTOSTART=1")
    start_registry(capfd)

    now = datetime.now()
    today = now.strftime("%Y-%m-%d")

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

    backend_start_date = get_container_start_date(capfd, "backend")
    rabbit_start_date = get_container_start_date(capfd, "rabbit")
    rabbit_pass1 = get_variable_from_projectrc("RABBITMQ_PASSWORD")

    exec_command(
        capfd,
        "password rabbit --random",
        "rabbit was running, restarting services...",
        "The password of rabbit has been changed. ",
        "Please find the new password into your .projectrc file as "
        "RABBITMQ_PASSWORD variable",
    )

    rabbit_pass2 = get_variable_from_projectrc("RABBITMQ_PASSWORD")
    assert rabbit_pass1 != rabbit_pass2

    backend_start_date2 = get_container_start_date(capfd, "backend", wait=True)
    rabbit_start_date2 = get_container_start_date(capfd, "rabbit", wait=False)

    # Verify that both backend and rabbit are restarted
    assert backend_start_date2 != backend_start_date
    assert rabbit_start_date2 != rabbit_start_date

    service_verify(capfd, "rabbitmq")

    exec_command(
        capfd,
        "password",
        f"rabbit     RABBITMQ_PASSWORD      {colors.GREEN}{today}",
    )

    # Needed to prevent random:
    # failed to update service xyz_rabbit:
    # Error response from daemon:
    # rpc error: code = Unknown desc = update out of sequence
    if Configuration.swarm_mode:
        time.sleep(3)

    mypassword = faker.pystr()
    exec_command(
        capfd,
        f"password rabbit --password {mypassword}",
        "The password of rabbit has been changed. ",
    )
    assert mypassword == get_variable_from_projectrc("RABBITMQ_PASSWORD")

    exec_command(
        capfd,
        "password --show",
        mypassword,
    )

    if Configuration.swarm_mode:
        time.sleep(5)

    service_verify(capfd, "rabbitmq")

    future = now + timedelta(days=PASSWORD_EXPIRATION + 1)
    expired = (now + timedelta(days=PASSWORD_EXPIRATION)).strftime("%Y-%m-%d")

    with freeze_time(future):
        exec_command(
            capfd,
            "password",
            f"rabbit     RABBITMQ_PASSWORD      {colors.RED}{today}",
        )

        exec_command(
            capfd,
            "check -i main --no-git --no-builds",
            f"RABBITMQ_PASSWORD is expired on {expired}",
        )

    # Cleanup the stack for the next test
    exec_command(capfd, "remove", "Stack removed")


def test_rabbit_invalid_characters(capfd: Capture, faker: Faker) -> None:

    create_project(
        capfd=capfd,
        name=random_project_name(faker),
        auth="no",
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
