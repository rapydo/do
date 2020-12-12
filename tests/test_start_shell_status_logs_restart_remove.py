"""
This module will test the interaction with containers
by executing the following commands:
- start
- status and logs
- shell
- restart
- remove
"""
import signal
import time
from datetime import datetime

from tests import create_project, exec_command, mock_KeyboardInterrupt, signal_handler


def test_all(capfd):

    create_project(
        capfd=capfd,
        name="first",
        auth="postgres",
        frontend="angular",
        services=["rabbit", "neo4j"],
        init=True,
        pull=True,
        start=False,
    )

    exec_command(
        capfd,
        "-s invalid start",
        "No such service: invalid",
    )

    exec_command(
        capfd,
        "start",
        "docker-compose command: 'up'",
        "Stack started",
    )

    exec_command(
        capfd,
        "-s backend start --force",
        "docker-compose command: 'up'",
        "Stack started",
    )

    exec_command(
        capfd,
        "status",
        "docker-compose command: 'ps'",
        # "first_backend_1",
    )

    # Added for GitHub Actions
    exec_command(
        capfd,
        "shell backend hostname",
        "the input device is not a TTY",
    )

    # --no-tty is needed on GitHub Actions
    exec_command(
        capfd,
        "shell --no-tty backend --command hostname",
        "Deprecated use of --command",
    )
    exec_command(
        capfd,
        "shell --no-tty backend --command 'hostname --short'",
        "Deprecated use of --command",
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
    # No default user for rabbit container
    exec_command(
        capfd,
        "shell --no-tty rabbit whoami",
        "root",
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
        "status",
        "docker-compose command: 'ps'",
        # "first_backend_1",
    )

    time.sleep(2)
    # Backend logs are never timestamped
    exec_command(
        capfd,
        "logs -s backend --tail 10 --no-color",
        "docker-compose command: 'logs'",
        "backend_1       | Development mode",
    )

    now = datetime.now()
    timestamp = now.strftime("%Y-%m-%dT")

    # Frontend logs are timestamped
    exec_command(
        capfd,
        "-s frontend logs --tail 10 --no-color",
        "docker-compose command: 'logs'",
        f"frontend_1      | {timestamp}",
    )

    # With multiple services logs are not timestamped
    exec_command(
        capfd,
        "-s frontend,backend logs --tail 10 --no-color",
        "docker-compose command: 'logs'",
        "backend_1       | Development mode",
        "frontend_1      | Merging files...",
    )

    signal.signal(signal.SIGALRM, mock_KeyboardInterrupt)
    signal.alarm(3)
    # Here using main services option
    exec_command(
        capfd,
        "-s backend logs --tail 10 --follow",
        "docker-compose command: 'logs'",
        "Stopped by keyboard",
    )

    exec_command(
        capfd,
        "-s backend remove --net",
        "Incompatibile options --networks and --service",
    )

    exec_command(
        capfd,
        "-s backend remove --all",
        "Incompatibile options --all and --service",
    )

    exec_command(
        capfd,
        "remove",
        "docker-compose command: 'stop'",
        "Stack removed",
    )

    exec_command(
        capfd,
        "remove --networks",
        "Stack removed",
    )

    exec_command(capfd, "remove --all", "Stack removed")

    exec_command(
        capfd,
        "shell --no-tty backend hostname",
        "No container found for backend_1",
    )
