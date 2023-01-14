"""
This module will test the password command and the passwords management
"""
import time
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
    service_verify,
    start_project,
    start_registry,
)


def test_password_neo4j(capfd: Capture, faker: Faker) -> None:

    project_name = random_project_name(faker)
    create_project(
        capfd=capfd,
        name=project_name,
        auth="neo4j",
        frontend="no",
    )

    init_project(capfd, "-e API_AUTOSTART=1")
    start_registry(capfd)

    now = datetime.now()
    today = now.strftime("%Y-%m-%d")

    if Configuration.swarm_mode:
        prefix = "│ neo4j    │"
    else:
        prefix = "│ neo4j   │"

    exec_command(
        capfd,
        "password neo4j --random",
        "Can't update neo4j because it is not running. Please start your stack",
    )

    exec_command(
        capfd,
        "password",
        f"{prefix} NEO4J_PASSWORD        │ N/A",
    )

    pull_images(capfd)
    start_project(capfd)

    service_verify(capfd, "neo4j")

    backend_start_date = get_container_start_date(capfd, "backend")
    neo4j_start_date = get_container_start_date(capfd, "neo4j")
    neo4j_pass1 = get_variable_from_projectrc("NEO4J_PASSWORD")

    exec_command(
        capfd,
        "password neo4j --random",
        "neo4j was running, restarting services...",
        "The password of neo4j has been changed. ",
        "Please find the new password into your .projectrc file as "
        "NEO4J_PASSWORD variable",
    )

    neo4j_pass2 = get_variable_from_projectrc("NEO4J_PASSWORD")
    assert neo4j_pass1 != neo4j_pass2

    backend_start_date2 = get_container_start_date(capfd, "backend", wait=True)
    neo4j_start_date2 = get_container_start_date(capfd, "neo4j", wait=False)

    # Verify that both backend and neo4j are restarted
    assert backend_start_date2 != backend_start_date
    assert neo4j_start_date2 != neo4j_start_date

    service_verify(capfd, "neo4j")

    exec_command(
        capfd,
        "password",
        f"{prefix} NEO4J_PASSWORD        │ {today}",
    )

    mypassword = faker.pystr(min_chars=12, max_chars=12)
    exec_command(
        capfd,
        f"password neo4j --password {mypassword}",
        "The password of neo4j has been changed. ",
    )
    assert mypassword == get_variable_from_projectrc("NEO4J_PASSWORD")

    exec_command(
        capfd,
        "password --show",
        mypassword,
    )

    if Configuration.swarm_mode:
        time.sleep(5)

    service_verify(capfd, "neo4j")

    PASSWORD_EXPIRATION = int(
        Application.env.get("PASSWORD_EXPIRATION_WARNING") or "180"
    )
    future = now + timedelta(days=PASSWORD_EXPIRATION + 1)
    expired = (now + timedelta(days=PASSWORD_EXPIRATION)).strftime("%Y-%m-%d")

    with freeze_time(future):
        exec_command(
            capfd,
            "password",
            f"{prefix} NEO4J_PASSWORD        │ {today}",
        )

        exec_command(
            capfd,
            "check -i main --no-git --no-builds",
            f"NEO4J_PASSWORD is expired on {expired}",
        )

    # TODO: should be verified that no red is shown
    exec_command(capfd, "-e PASSWORD_EXPIRATION_WARNING=0 password")

    # Cleanup the stack for the next test
    exec_command(capfd, "remove", "Stack removed")
