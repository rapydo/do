"""
This module will test the shell command
"""
import signal

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


def test_all(capfd: Capture) -> None:

    execute_outside(capfd, "shell backend ls")

    create_project(
        capfd=capfd,
        name="first",
        auth="postgres",
        frontend="angular",
        services=["rabbit", "neo4j"],
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
