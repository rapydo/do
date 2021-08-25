"""
This module will test the shell command
"""
import signal

from tests import (
    Capture,
    create_project,
    exec_command,
    init_project,
    pull_images,
    signal_handler,
    start_project,
)


def test_all(capfd: Capture) -> None:

    create_project(
        capfd=capfd,
        name="first",
        auth="postgres",
        frontend="angular",
        services=["rabbit", "neo4j"],
    )
    init_project(capfd)
    pull_images(capfd)
    start_project(capfd)

    # Added for GitHub Actions
    exec_command(
        capfd,
        "shell backend hostname",
        "the input device is not a TTY",
    )

    exec_command(
        capfd,
        "shell --no-tty backend hostname",
        "backend-server",
    )

    signal.signal(signal.SIGALRM, signal_handler)
    signal.alarm(2)
    exec_command(
        capfd,
        "shell --no-tty backend --default-command",
        # "*** RESTful HTTP API ***",
        # "Serving Flask app",
        "Time is up",
    )

    # This can't work on GitHub Actions due to the lack of tty
    # signal.signal(signal.SIGALRM, handler)
    # signal.alarm(2)
    # exec_command(
    #     capfd,
    #     "shell --no-tty backend",
    #     # "developer@backend-server:[/code]",
    #     "Time is up",
    # )

    # Testing default users
    exec_command(
        capfd,
        "shell --no-tty backend whoami",
        "developer",
    )
    exec_command(
        capfd,
        "shell --no-tty frontend whoami",
        "node",
    )
    exec_command(
        capfd,
        "shell --no-tty rabbit whoami",
        "rabbitmq",
    )
    exec_command(
        capfd,
        "shell --no-tty postgres whoami",
        "postgres",
    )
    exec_command(
        capfd,
        "shell --no-tty neo4j whoami",
        "neo4j",
    )

    exec_command(
        capfd,
        "remove",
        "Stack removed",
    )

    exec_command(
        capfd,
        "shell --no-tty backend hostname",
        "Requested command: hostname with user: developer",
        "No container found for backend_1",
    )

    exec_command(
        capfd,
        "shell --no-tty backend --default",
        "Requested command: restapi launch with user: developer",
        "No container found for backend_1",
    )
