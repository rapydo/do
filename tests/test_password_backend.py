"""
This module will test the password command and the passwords management
"""
import time
from datetime import datetime

import requests
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
    start_project,
    start_registry,
    wait_until,
)


def test_password_backend(capfd: Capture, faker: Faker) -> None:

    project_name = random_project_name(faker)
    create_project(
        capfd=capfd,
        name=project_name,
        auth="postgres",
        frontend="no",
    )

    init_project(capfd, "-e API_AUTOSTART=1")
    start_registry(capfd)

    today = datetime.now().strftime("%Y-%m-%d")

    exec_command(
        capfd,
        "password backend --random",
        "Can't update backend because it is not running. Please start your stack",
    )

    exec_command(
        capfd,
        "password",
        f"backend    AUTH_DEFAULT_PASSWORD  {colors.RED}N/A",
    )

    pull_images(capfd)
    start_project(capfd)

    # This is needed to wait for the service rolling update
    if SWARM_MODE:
        time.sleep(5)

    wait_until(capfd, "logs backend --tail 10", "Boot completed")

    exec_command(capfd, "logs backend --tail 10")

    r = requests.post(
        "http://127.0.0.1:8080/auth/login",
        data={
            "username": get_variable_from_projectrc("AUTH_DEFAULT_USERNAME"),
            "password": get_variable_from_projectrc("AUTH_DEFAULT_PASSWORD"),
        },
    )
    exec_command(capfd, "logs backend --tail 10")
    assert r.status_code == 200

    backend_start_date = get_container_start_date(capfd, "backend")
    backend_pass1 = get_variable_from_projectrc("AUTH_DEFAULT_PASSWORD")

    exec_command(
        capfd,
        "password backend --random",
        "backend was running, restarting services...",
        "The password of backend has been changed. ",
        "Please find the new password into your .projectrc file as "
        "AUTH_DEFAULT_PASSWORD variable",
    )

    backend_pass2 = get_variable_from_projectrc("AUTH_DEFAULT_PASSWORD")
    assert backend_pass1 != backend_pass2

    backend_start_date2 = get_container_start_date(capfd, "backend", wait=True)

    # Verify that backend is restarted
    assert backend_start_date2 != backend_start_date

    # This is needed to wait for the service rolling update
    if SWARM_MODE:
        time.sleep(5)
    wait_until(capfd, "logs backend --tail 10", "Boot completed")

    r = requests.post(
        "http://127.0.0.1:8080/auth/login",
        data={
            "username": get_variable_from_projectrc("AUTH_DEFAULT_USERNAME"),
            "password": get_variable_from_projectrc("AUTH_DEFAULT_PASSWORD"),
        },
    )
    exec_command(capfd, "logs backend --tail 10")
    assert r.status_code == 200

    exec_command(
        capfd,
        "password",
        f"backend    AUTH_DEFAULT_PASSWORD  {colors.GREEN}{today}",
    )

    mypassword = faker.pystr()
    exec_command(
        capfd,
        f"password backend --password {mypassword}",
        "The password of backend has been changed. ",
    )
    assert mypassword == get_variable_from_projectrc("AUTH_DEFAULT_PASSWORD")

    exec_command(
        capfd,
        "password --show",
        mypassword,
    )

    wait_until(capfd, "logs backend --tail 10", "Boot completed")

    r = requests.post(
        "http://127.0.0.1:8080/auth/login",
        data={
            "username": get_variable_from_projectrc("AUTH_DEFAULT_USERNAME"),
            "password": get_variable_from_projectrc("AUTH_DEFAULT_PASSWORD"),
        },
    )
    exec_command(capfd, "logs backend --tail 10")
    assert r.status_code == 200

    # Cleanup the stack for the next test
    exec_command(capfd, "remove", "Stack removed")
