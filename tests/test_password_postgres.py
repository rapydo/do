"""
This module will test the password command and the passwords management
"""
import time
from datetime import datetime

from faker import Faker

from controller import SWARM_MODE, colors
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

    backend_start_date = get_container_start_date(capfd, "backend", project_name)
    postgres_start_date = get_container_start_date(capfd, "postgres", project_name)
    postgres_pass1 = get_variable_from_projectrc("ALCHEMY_PASSWORD")

    exec_command(
        capfd,
        "password postgres --random",
        "postgres was running, restarting services...",
        "The password of postgres has been changed. ",
        "Please find the new password into your .projectrc file as "
        "ALCHEMY_PASSWORD variable",
    )

    postgres_pass2 = get_variable_from_projectrc("ALCHEMY_PASSWORD")
    assert postgres_pass1 != postgres_pass2

    backend_start_date2 = get_container_start_date(
        capfd, "backend", project_name, wait=True
    )
    postgres_start_date2 = get_container_start_date(
        capfd, "postgres", project_name, wait=False
    )

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
    assert mypassword == get_variable_from_projectrc("ALCHEMY_PASSWORD")

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
