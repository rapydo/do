"""
This module will test the reload command
"""
import time

from faker import Faker

from controller import SWARM_MODE
from controller.deploy.docker import Docker
from tests import (
    Capture,
    create_project,
    exec_command,
    execute_outside,
    init_project,
    pull_images,
    random_project_name,
    start_project,
    start_registry,
)


def test_base(capfd: Capture, faker: Faker) -> None:

    execute_outside(capfd, "reload")

    project_name = random_project_name(faker)

    create_project(
        capfd=capfd,
        name=project_name,
        auth="no",
        frontend="no",
        services=["fail2ban"],
    )
    init_project(capfd)

    exec_command(capfd, "reload", "No service reloaded")
    exec_command(capfd, "reload backend", "No service reloaded")
    exec_command(capfd, "reload invalid", "No such service: invalid")
    exec_command(capfd, "reload backend invalid", "No such service: invalid")

    start_registry(capfd)
    pull_images(capfd)

    start_project(capfd)

    exec_command(capfd, "reload backend", "Reloading Flask...")

    if SWARM_MODE:
        service = "backend"

        exec_command(
            capfd,
            "start backend",
            "Stack started",
        )

        exec_command(
            capfd,
            "scale backend=2 --wait",
            f"{project_name}_backend scaled to 2",
            "Service converged",
        )
    else:

        service = "fail2ban"
        exec_command(
            capfd,
            "scale fail2ban=2",
            "Scaling services: fail2ban=2...",
            "Services scaled: fail2ban=2",
        )

    time.sleep(4)

    docker = Docker()
    container1 = docker.get_container(service, slot=1)
    container2 = docker.get_container(service, slot=2)
    assert container1 is not None
    assert container2 is not None
    assert container1 != container2

    exec_command(
        capfd,
        f"reload {service}",
        f"Executing on {container1[0]}",
        f"Executing on {container2[0]}",
    )

    exec_command(capfd, "shell backend -u root 'rm /usr/local/bin/reload'")

    exec_command(
        capfd, "reload backend", "Service backend does not support the reload command"
    )

    exec_command(capfd, "remove", "Stack removed")


def test_reload_dev(capfd: Capture, faker: Faker) -> None:
    create_project(
        capfd=capfd,
        name=random_project_name(faker),
        auth="no",
        frontend="no",
    )
    init_project(capfd)
    start_registry(capfd)

    pull_images(capfd)

    start_project(capfd)

    time.sleep(5)

    # For each support service verify:
    #   1) a start line in the logs
    #   2) the container is not re-created after the command
    #   3) the start line in the logs is printed again
    #   4) some more deep check based on the service?
    #      For example API is loading a change in the code?
    exec_command(capfd, "reload backend", "Reloading Flask...")

    exec_command(capfd, "remove", "Stack removed")

    if SWARM_MODE:
        exec_command(capfd, "remove registry", "Service registry removed")


def test_reload_prod(capfd: Capture, faker: Faker) -> None:
    create_project(
        capfd=capfd,
        name=random_project_name(faker),
        auth="no",
        frontend="no",
    )

    init_project(capfd, " --prod ", "--force")

    start_registry(capfd)
    pull_images(capfd)

    start_project(capfd)

    time.sleep(5)

    exec_command(capfd, "reload backend", "Reloading gunicorn (PID #")

    exec_command(capfd, "remove", "Stack removed")
