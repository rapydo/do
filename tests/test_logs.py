"""
This module will test the logs command
"""
import signal
from datetime import datetime

from controller import SWARM_MODE
from tests import (
    Capture,
    create_project,
    exec_command,
    execute_outside,
    init_project,
    mock_KeyboardInterrupt,
    pull_images,
    start_project,
    start_registry,
)


def test_all(capfd: Capture) -> None:

    execute_outside(capfd, "logs backend")

    create_project(
        capfd=capfd,
        name="first",
        auth="postgres",
        frontend="angular",
    )
    init_project(capfd)

    start_registry(capfd)

    pull_images(capfd)
    start_project(capfd)

    # Invalid services are refused
    exec_command(
        capfd,
        "logs --tail 1 invalid",
        "No such service: invalid",
    )

    now = datetime.now()

    # In swarm mode this test hangs forever, even if KeyboardInterrupt is correctly
    # catched and working if manually tested
    if not SWARM_MODE:

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

    exec_command(capfd, "logs --tail 2 backend", "first_backend", "Testing mode")

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

    # Backend logs are never timestamped
    exec_command(
        capfd,
        "logs --tail 20 backend",
        # Logs are not prefixed because only one service is shown
        "Testing mode",
    )

    # Debug code... no logs in swarm mode for frontend, even after a wait 20...
    if SWARM_MODE:
        exec_command(
            capfd,
            "logs --tail 10 frontend",
        )
    else:
        timestamp = now.strftime("%Y-%m-%dT")
        # Frontend logs are always timestamped
        exec_command(
            capfd,
            "logs --tail 10 frontend",
            # Logs are not prefixed because only one service is shown
            f"{timestamp}",
        )

    # Follow flag is not supported in swarm mode with multiple services
    if SWARM_MODE:
        # Multiple services are not supported in swarm mode
        exec_command(
            capfd,
            "logs --follow",
            "Follow flag is not supported on multiple services",
        )

        exec_command(
            capfd,
            "logs --follow backend frontend",
            "Follow flag is not supported on multiple services",
        )
