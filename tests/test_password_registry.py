"""
This module will test the password command and the passwords management
"""
from datetime import datetime, timedelta

from faker import Faker
from freezegun import freeze_time
from python_on_whales import docker

from controller import colors
from controller.app import Configuration
from controller.commands.password import PASSWORD_EXPIRATION
from tests import (
    REGISTRY,
    Capture,
    create_project,
    exec_command,
    get_container_start_date,
    get_variable_from_projectrc,
    init_project,
    random_project_name,
    start_registry,
)


def test_password_registry(capfd: Capture, faker: Faker) -> None:

    if not Configuration.swarm_mode:
        return None

    project_name = random_project_name(faker)
    create_project(
        capfd=capfd,
        name=project_name,
        auth="postgres",
        frontend="no",
    )

    init_project(capfd)

    today = datetime.now().strftime("%Y-%m-%d")

    exec_command(
        capfd,
        "password",
        f"registry   REGISTRY_PASSWORD      {colors.RED}N/A",
    )
    registry_pass1 = get_variable_from_projectrc("REGISTRY_PASSWORD")

    docker.container.remove(REGISTRY, force=True)

    exec_command(
        capfd,
        "password registry --random",
        "registry was not running, restart is not needed",
        "The password of registry has been changed. ",
        "Please find the new password into your .projectrc file as "
        "REGISTRY_PASSWORD variable",
    )
    registry_pass2 = get_variable_from_projectrc("REGISTRY_PASSWORD")
    assert registry_pass1 != registry_pass2

    start_registry(capfd)

    exec_command(
        capfd,
        "password",
        f"registry   REGISTRY_PASSWORD      {colors.GREEN}{today}",
    )

    exec_command(capfd, "images", "This registry contains ")

    registry_start_date = get_container_start_date(capfd, "registry", wait=True)

    exec_command(
        capfd,
        "password registry --random",
        "registry was running, restarting services...",
        "The password of registry has been changed. ",
        "Please find the new password into your .projectrc file as "
        "REGISTRY_PASSWORD variable",
    )

    registry_pass3 = get_variable_from_projectrc("REGISTRY_PASSWORD")
    assert registry_pass2 != registry_pass3

    registry_start_date2 = get_container_start_date(capfd, "registry", wait=True)

    assert registry_start_date2 != registry_start_date

    exec_command(capfd, "images", "This registry contains ")

    exec_command(
        capfd,
        "password",
        f"registry   REGISTRY_PASSWORD      {colors.GREEN}{today}",
    )

    variable = "REGISTRY_PASSWORD"
    label = "registry"

    future = datetime.now() + timedelta(days=PASSWORD_EXPIRATION + 1)

    with freeze_time(future.strftime("%Y-%m-%d")):
        exec_command(
            capfd,
            "password",
            f"{label}    {variable}  {colors.RED}{today}",
        )

        exec_command(
            capfd,
            "check -i main --no-git --no-builds",
            f"{variable} is expired on {today}",
        )

    # This is needed otherwise the following tests will be unable to start
    # a new instance of the registry and will fail with registry auth errors
    exec_command(capfd, "remove registry", "Service registry removed")
