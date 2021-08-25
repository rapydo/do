"""
This module will test the logs command
"""
import signal
import time
from datetime import datetime

from tests import (
    Capture,
    create_project,
    exec_command,
    init_project,
    mock_KeyboardInterrupt,
    pull_images,
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

    time.sleep(5)
    # Backend logs are never timestamped
    exec_command(
        capfd,
        # logs with tail 200 needed due to the spam of Requirement installation
        # after the Collecting ... /http-api.git
        "logs --tail 200 --no-color backend",
        "docker-compose command: 'logs'",
        # Logs are not prefixed because only one service is shown
        "Testing mode",
    )

    now = datetime.now()
    timestamp = now.strftime("%Y-%m-%dT")

    # Frontend logs are always timestamped
    exec_command(
        capfd,
        "logs --tail 10 --no-color frontend",
        "docker-compose command: 'logs'",
        # Logs are not prefixed because only one service is shown
        f"{timestamp}",
    )

    # With multiple services logs are not timestamped
    exec_command(
        capfd,
        "logs --tail 10 --no-color frontend backend",
        "docker-compose command: 'logs'",
        # Logs are prefixed because more than one service is shown
        "backend_1      | Testing mode",
        # "backend_1       | Development mode",
        "frontend_1     | Merging files...",
    )

    signal.signal(signal.SIGALRM, mock_KeyboardInterrupt)
    signal.alarm(5)
    # Here using main services option
    exec_command(
        capfd,
        "logs --tail 10 --follow backend",
        "docker-compose command: 'logs'",
        "Stopped by keyboard",
    )

    # Invalid services are refused
    exec_command(
        capfd,
        "logs --tail 1 invalid",
        "No such service: invalid",
    )

    exec_command(
        capfd,
        "logs --tail 1",
        "Enabled services: ['backend', 'frontend', 'neo4j', 'postgres', 'rabbit']",
    )

    exec_command(
        capfd,
        "logs --tail 1 backend",
        "Enabled services: ['backend']",
    )

    exec_command(
        capfd,
        "logs --tail 1 frontend",
        "Enabled services: ['frontend']",
    )

    exec_command(
        capfd,
        "logs --tail 1 backend frontend",
        "Enabled services: ['backend', 'frontend']",
    )

    exec_command(
        capfd,
        "logs --tail 1 frontend backend",
        "Enabled services: ['backend', 'frontend']",
    )

    exec_command(
        capfd,
        "logs --tail 1 backend invalid",
        "No such service: invalid",
    )

    exec_command(
        capfd,
        "remove --all backend",
        "Stack removed",
    )
