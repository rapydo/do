"""
This module will test the password command and the passwords management
"""
from datetime import datetime, timedelta

from faker import Faker
from freezegun import freeze_time

from controller.app import Application, Configuration
from tests import (
    Capture,
    create_project,
    exec_command,
    get_container_start_date,
    get_variable_from_projectrc,
    init_project,
    pull_images,
    random_project_name,
    start_project,
    start_registry,
)


def test_password_flower(capfd: Capture, faker: Faker) -> None:

    project_name = random_project_name(faker)
    create_project(
        capfd=capfd,
        name=project_name,
        auth="no",
        frontend="no",
        services=["flower"],
    )

    init_project(capfd, "-e API_AUTOSTART=1")
    start_registry(capfd)

    now = datetime.now()
    today = now.strftime("%Y-%m-%d")

    if Configuration.swarm_mode:
        prefix = "│ flower   │"
    else:
        prefix = "│ flower  │"
    exec_command(capfd, "password", f"{prefix} FLOWER_PASSWORD       │ N/A")

    flower_pass1 = get_variable_from_projectrc("FLOWER_PASSWORD")
    exec_command(
        capfd,
        "password flower --random",
        "flower was not running, restart is not needed",
        "The password of flower has been changed. ",
        "Please find the new password into your .projectrc file as "
        "FLOWER_PASSWORD variable",
    )
    flower_pass2 = get_variable_from_projectrc("FLOWER_PASSWORD")
    assert flower_pass1 != flower_pass2

    exec_command(
        capfd,
        "password",
        f"{prefix} FLOWER_PASSWORD       │ {today}",
    )

    pull_images(capfd)
    start_project(capfd)

    flower_start_date = get_container_start_date(capfd, "flower", wait=True)

    exec_command(
        capfd,
        "password flower --random",
        "flower was running, restarting services...",
        "The password of flower has been changed. ",
        "Please find the new password into your .projectrc file as "
        "FLOWER_PASSWORD variable",
    )

    flower_pass3 = get_variable_from_projectrc("FLOWER_PASSWORD")
    assert flower_pass2 != flower_pass3

    flower_start_date2 = get_container_start_date(capfd, "flower", wait=True)

    assert flower_start_date2 != flower_start_date

    exec_command(
        capfd,
        "password",
        f"{prefix} FLOWER_PASSWORD       │ {today}",
    )

    mypassword = faker.pystr(min_chars=12, max_chars=12)
    exec_command(
        capfd,
        f"password flower --password {mypassword}",
        "The password of flower has been changed. ",
    )
    assert mypassword == get_variable_from_projectrc("FLOWER_PASSWORD")

    exec_command(
        capfd,
        "password --show",
        mypassword,
    )

    PASSWORD_EXPIRATION = int(
        Application.env.get("PASSWORD_EXPIRATION_WARNING") or "180"
    )
    future = now + timedelta(days=PASSWORD_EXPIRATION + 1)
    expired = (now + timedelta(days=PASSWORD_EXPIRATION)).strftime("%Y-%m-%d")

    with freeze_time(future):
        exec_command(
            capfd,
            "password",
            f"{prefix} FLOWER_PASSWORD       │ {today}",
        )

        exec_command(
            capfd,
            "check -i main --no-git --no-builds",
            f"FLOWER_PASSWORD is expired on {expired}",
        )

    # TODO: should be verified that no red is shown
    exec_command(capfd, "-e PASSWORD_EXPIRATION_WARNING=0 password")

    # Cleanup the stack for the next test
    exec_command(capfd, "remove", "Stack removed")
