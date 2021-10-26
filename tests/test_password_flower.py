"""
This module will test the password command and the passwords management
"""
from datetime import datetime

from faker import Faker

from controller import colors
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
        auth="postgres",
        frontend="no",
        services=["flower"],
    )

    init_project(capfd, "-e API_AUTOSTART=1")
    start_registry(capfd)

    today = datetime.now().strftime("%Y-%m-%d")

    exec_command(
        capfd,
        "password",
        f"flower     FLOWER_PASSWORD        {colors.RED}N/A",
    )

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
        f"flower     FLOWER_PASSWORD        {colors.GREEN}{today}",
    )

    pull_images(capfd)
    start_project(capfd)

    flower_start_date = get_container_start_date(
        capfd, "flower", project_name, wait=True
    )

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

    flower_start_date2 = get_container_start_date(
        capfd, "flower", project_name, wait=True
    )

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
    assert mypassword == get_variable_from_projectrc("FLOWER_PASSWORD")

    exec_command(
        capfd,
        "password --show",
        mypassword,
    )

    # Cleanup the stack for the next test
    exec_command(capfd, "remove", "Stack removed")
