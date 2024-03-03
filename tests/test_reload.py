"""
This module will test the reload command
"""
import time

from faker import Faker

from controller.app import Configuration
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

    if Configuration.swarm_mode:
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
        f"Executing command on {container1[0]}",
        f"Executing command on {container2[0]}",
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

    if Configuration.swarm_mode:
        exec_command(capfd, "remove registry", "Service registry removed")


def test_reload_prod(capfd: Capture, faker: Faker) -> None:
    create_project(
        capfd=capfd,
        name=random_project_name(faker),
        auth="no",
        frontend="angular",
    )

    init_project(capfd, " --prod ", "--force")

    start_registry(capfd)
    pull_images(capfd)

    start_project(capfd)

    time.sleep(5)

    exec_command(capfd, "reload backend", "Reloading gunicorn (PID #")

    exec_command(
        capfd,
        "reload",
        "Can't reload the frontend if not explicitly requested",
        "Services reloaded",
    )

    docker = Docker()
    container = docker.get_container("frontend")
    assert container is not None

    docker.client.container.stop(container[0])
    exec_command(capfd, "reload frontend", "Reloading frontend...")

    container = docker.get_container("frontend")

    if Configuration.swarm_mode:
        # frontend reload is always execute in compose mode
        # => the container retrieved from docker.get_container in swarm mode is None
        assert container is None
        # Let's retrieve the container name in compose mode:

        Configuration.swarm_mode = False
        docker = Docker()
        container = docker.get_container("frontend")

        # Let's restore the docker client
        Configuration.swarm_mode = True
        docker = Docker()

    assert container is not None

    docker.client.container.remove(container[0], force=True)
    exec_command(capfd, "reload frontend", "Reloading frontend...")

    exec_command(
        capfd,
        "reload frontend backend",
        "Can't reload frontend and other services at once",
    )
    exec_command(capfd, "remove", "Stack removed")
