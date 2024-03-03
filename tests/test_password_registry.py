"""
This module will test the password command and the passwords management
"""
from datetime import datetime, timedelta

from faker import Faker
from freezegun import freeze_time
from python_on_whales import docker

from controller.app import Application, Configuration
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
    # load variables and initialize the Configuration
    Application()
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

    now = datetime.now()
    today = now.strftime("%Y-%m-%d")

    exec_command(
        capfd,
        "password",
        "│ registry │ REGISTRY_PASSWORD     │ N/A",
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
        f"│ registry │ REGISTRY_PASSWORD     │ {today}",
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
        f"│ registry │ REGISTRY_PASSWORD     │ {today}",
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
            f"│ registry │ REGISTRY_PASSWORD     │ {today}",
        )

        exec_command(
            capfd,
            "check -i main --no-git --no-builds",
            f"REGISTRY_PASSWORD is expired on {expired}",
        )

    # TODO: should be verified that no red is shown
    exec_command(capfd, "-e PASSWORD_EXPIRATION_WARNING=0 password")

    # This is needed otherwise the following tests will be unable to start
    # a new instance of the registry and will fail with registry auth errors
    exec_command(capfd, "remove registry", "Service registry removed")
