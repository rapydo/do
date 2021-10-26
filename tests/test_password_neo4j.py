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

    backend_start_date = get_container_start_date(capfd, "backend", project_name)
    neo4j_start_date = get_container_start_date(capfd, "neo4j", project_name)
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

    backend_start_date2 = get_container_start_date(
        capfd, "backend", project_name, wait=True
    )
    neo4j_start_date2 = get_container_start_date(
        capfd, "neo4j", project_name, wait=False
    )

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
    assert mypassword == get_variable_from_projectrc("NEO4J_PASSWORD")

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
