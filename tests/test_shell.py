"""
This module will test the shell command
"""
import signal

from controller import SWARM_MODE
from tests import (
    Capture,
    create_project,
    exec_command,
    init_project,
    pull_images,
    signal_handler,
    start_project,
    start_registry,
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
    if SWARM_MODE:
        start_registry(capfd)
    pull_images(capfd)
    start_project(capfd)

    if SWARM_MODE:
        exec_command(capfd, "shell invalid", "Service invalid not found")
    else:
        exec_command(capfd, "shell invalid", "No such service: invalid")

    if SWARM_MODE:

        exec_command(
            capfd,
            "shell backend",
            "Due to limitations of the underlying packages, "
            "the shell command is not implemented yet",
            "You can execute by yourself the following command",
            "docker exec --interactive --tty --user developer swarm_backend.1.",
            "bash",
        )

        exec_command(
            capfd,
            "shell backend --default",
            "Due to limitations of the underlying packages, "
            "the shell command is not implemented yet",
            "You can execute by yourself the following command",
            "docker exec --interactive --tty --user developer swarm_backend.1.",
            "restapi launch",
        )

        exec_command(capfd, "shell backend -u aRandomUser", "--user aRandomUser")

    else:
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
