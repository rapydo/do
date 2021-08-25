"""
This module will test the logs command
"""
import signal
import time
from datetime import datetime

from controller import SWARM_MODE
from tests import (
    Capture,
    create_project,
    exec_command,
    init_project,
    mock_KeyboardInterrupt,
    pull_images,
    start_project,
    start_registry,
)


def test_all(capfd: Capture) -> None:

    create_project(
        capfd=capfd,
        name="first",
        auth="postgres",
        frontend="angular",
    )
    init_project(capfd)

    if SWARM_MODE:
        start_registry(capfd)

    pull_images(capfd)
    start_project(capfd)

    # Wait for the backend startup
    # In compose mode this sleep was 3 seconds,
    # but in swarm it is not enough due to the slow deployment phase
    time.sleep(20)

    # Invalid services are refused
    exec_command(
        capfd,
        "logs --tail 1 invalid",
        "No such service: invalid",
    )

    if not SWARM_MODE:
        now = datetime.now()
        timestamp = now.strftime("%Y-%m-%dT")

        signal.signal(signal.SIGALRM, mock_KeyboardInterrupt)
        signal.alarm(5)
        # Here using main services option
        exec_command(
            capfd,
            "logs --tail 10 --follow backend",
            "REST API backend server is ready to be launched",
        )
        end = datetime.now()

        assert (end - now).seconds >= 2

    exec_command(
        capfd,
        "logs backend",
        "REST API backend server is ready to be launched",
    )

    exec_command(
        capfd,
        "logs --tail 1",
        "Enabled services: ['backend', 'frontend', 'postgres']",
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

    if not SWARM_MODE:

        # Backend logs are never timestamped
        exec_command(
            capfd,
            "logs --tail 20 backend",
            # Logs are not prefixed because only one service is shown
            "Testing mode",
        )

        # Frontend logs are always timestamped
        exec_command(
            capfd,
            "logs --tail 10 --no-color frontend",
            # Logs are not prefixed because only one service is shown
            f"{timestamp}",
        )

        # With multiple services logs are not timestamped
        exec_command(
            capfd,
            "logs --tail 10 --no-color frontend backend",
            # Logs are prefixed because more than one service is shown
            "backend_1      | Testing mode",
            # "backend_1       | Development mode",
            "frontend_1     | Merging files...",
        )
