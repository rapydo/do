"""
This module will test the password command and the passwords management
"""
import time
from datetime import datetime, timedelta

from faker import Faker
from freezegun import freeze_time

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


def test_password_mysql(capfd: Capture, faker: Faker) -> None:

    project_name = random_project_name(faker)
    create_project(
        capfd=capfd,
        name=project_name,
        auth="mysql",
        frontend="no",
    )

    init_project(capfd, "-e API_AUTOSTART=1")
    start_registry(capfd)

    now = datetime.now()
    today = now.strftime("%Y-%m-%d")
    if Configuration.swarm_mode:
        prefix = "│ mariadb  │"
    else:
        prefix = "│ mariadb │"

    exec_command(
        capfd,
        "password mariadb --random",
        "Can't update mariadb because it is not running. Please start your stack",
    )

    exec_command(
        capfd,
        "password",
        f"{prefix} ALCHEMY_PASSWORD      │ N/A",
    )

    pull_images(capfd)
    start_project(capfd)

    service_verify(capfd, "sqlalchemy")

    backend_start_date = get_container_start_date(capfd, "backend")
    mariadb_start_date = get_container_start_date(capfd, "mariadb")
    mariadb_pass1 = get_variable_from_projectrc("ALCHEMY_PASSWORD")

    exec_command(
        capfd,
        "password mariadb --random",
        "mariadb was running, restarting services...",
        "The password of mariadb has been changed. ",
        "Please find the new password into your .projectrc file as "
        "ALCHEMY_PASSWORD variable",
    )

    mariadb_pass2 = get_variable_from_projectrc("ALCHEMY_PASSWORD")
    assert mariadb_pass1 != mariadb_pass2

    backend_start_date2 = get_container_start_date(capfd, "backend", wait=True)
    mariadb_start_date2 = get_container_start_date(capfd, "mariadb", wait=False)

    # Verify that both backend and mariadb are restarted
    assert backend_start_date2 != backend_start_date
    assert mariadb_start_date2 != mariadb_start_date

    service_verify(capfd, "sqlalchemy")

    exec_command(
        capfd,
        "password",
        f"{prefix} ALCHEMY_PASSWORD      │ {today}",
    )

    mypassword = faker.pystr(min_chars=12, max_chars=12)
    exec_command(
        capfd,
        f"password mariadb --password {mypassword}",
        "The password of mariadb has been changed. ",
    )
    assert mypassword == get_variable_from_projectrc("ALCHEMY_PASSWORD")

    exec_command(
        capfd,
        "password --show",
        mypassword,
    )

    if Configuration.swarm_mode:
        time.sleep(5)

    service_verify(capfd, "sqlalchemy")

    future = now + timedelta(days=PASSWORD_EXPIRATION + 1)
    expired = (now + timedelta(days=PASSWORD_EXPIRATION)).strftime("%Y-%m-%d")

    with freeze_time(future):
        exec_command(
            capfd,
            "password",
            f"{prefix} ALCHEMY_PASSWORD      │ {today}",
        )

        exec_command(
            capfd,
            "check -i main --no-git --no-builds",
            f"ALCHEMY_PASSWORD is expired on {expired}",
        )

    # Cleanup the stack for the next test
    exec_command(capfd, "remove", "Stack removed")
