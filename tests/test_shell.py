"""
This module will test the shell command
"""
import signal

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
    signal_handler,
    start_project,
    start_registry,
)


def test_all(capfd: Capture, faker: Faker) -> None:

    execute_outside(capfd, "shell backend ls")

    create_project(
        capfd=capfd,
        name="first",
        auth="postgres",
        frontend="angular",
        services=["rabbit", "neo4j", "redis"],
    )
    init_project(capfd)

    start_registry(capfd)

    pull_images(capfd)
    start_project(capfd)

    exec_command(
        capfd, "shell invalid", "No running container found for invalid service"
    )

    exec_command(
        capfd,
        "shell --no-tty backend invalid",
        "--no-tty option is deprecated, you can stop using it",
    )

    exec_command(
        capfd,
        "shell backend invalid",
        "The command execution was terminated by command cannot be invoked. "
        "Exit code is 126",
    )

    exec_command(
        capfd,
        'shell backend "bash invalid"',
        "The command execution was terminated by command not found. "
        "Exit code is 127",
    )

    exec_command(
        capfd,
        "shell backend hostname",
        "backend-server",
    )

    signal.signal(signal.SIGALRM, signal_handler)
    signal.alarm(2)
    exec_command(
        capfd,
        "shell backend --default-command",
        "Time is up",
    )

    # This can't work on GitHub Actions due to the lack of tty
    # signal.signal(signal.SIGALRM, handler)
    # signal.alarm(2)
    # exec_command(
    #     capfd,
    #     "shell backend",
    #     # "developer@backend-server:[/code]",
    #     "Time is up",
    # )

    # Testing default users
    exec_command(
        capfd,
        "shell backend whoami",
        "developer",
    )

    exec_command(
        capfd,
        "shell frontend whoami",
        "node",
    )

    exec_command(
        capfd,
        "shell rabbit whoami",
        "rabbitmq",
    )

    exec_command(
        capfd,
        "shell postgres whoami",
        "postgres",
    )

    exec_command(
        capfd,
        "shell neo4j whoami",
        "neo4j",
    )

    exec_command(
        capfd,
        "remove",
        "Stack removed",
    )

    exec_command(
        capfd,
        "shell backend hostname",
        "Requested command: hostname with user: developer",
        "No running container found for backend service",
    )

    exec_command(
        capfd,
        "shell backend --default",
        "Requested command: restapi launch with user: developer",
        "No running container found for backend service",
    )

    exec_command(
        capfd,
        "shell backend --replica 1 --default",
        "Requested command: restapi launch with user: developer",
        "No running container found for backend service",
    )

    exec_command(
        capfd,
        "shell backend --replica 2 --default",
        "Requested command: restapi launch with user: developer",
        "Replica number 2 not found for backend service",
    )

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
            "first_backend scaled to 2",
            "Service converged",
        )
    else:

        service = "redis"
        exec_command(
            capfd,
            "scale redis=2",
            "Scaling services: redis=2...",
            "Services scaled: redis=2",
        )

    docker = Docker()
    container1 = docker.get_container(service, slot=1)
    container2 = docker.get_container(service, slot=2)
    assert container1 is not None
    assert container2 is not None
    assert container1 != container2

    string1 = faker.pystr(min_chars=30, max_chars=30)
    string2 = faker.pystr(min_chars=30, max_chars=30)

    docker.client.container.execute(
        container1,
        command=["touch", f"/tmp/{string1}"],
        tty=False,
        detach=False,
    )

    docker.client.container.execute(
        container2,
        command=["touch", f"/tmp/{string2}"],
        tty=False,
        detach=False,
    )

    exec_command(capfd, f"shell {service} --replica 1 'ls /tmp/'", string1)

    exec_command(capfd, f"shell {service} --replica 2 'ls /tmp/'", string2)

    exec_command(
        capfd,
        f"shell {service} mycommand --replica 2 --broadcast",
        "--replica and --broadcast options are not compatible",
    )

    exec_command(
        capfd,
        f"shell {service} --broadcast 'ls /tmp/'",
        string1,
        string2,
    )

    exec_command(
        capfd,
        "remove",
        "Stack removed",
    )

    exec_command(
        capfd,
        f"shell {service} mycommand --broadcast",
        f"No running container found for {service} service",
    )
