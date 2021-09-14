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
    init_project(capfd, "-e HEALTHCHECK_INTERVAL=1s")

    if SWARM_MODE:
        start_registry(capfd)

    pull_images(capfd)
    start_project(capfd)

    time.sleep(3)

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

    # In swarm mode service is mandatory
    if SWARM_MODE:
        exec_command(
            capfd,
            "logs --tail 1",
            "Error: Missing argument 'SERVICE'",
        )
    else:
        exec_command(
            capfd,
            "logs --tail 1",
            "Enabled services: ['backend', 'frontend', 'postgres']",
        )

    if SWARM_MODE:
        exec_command(capfd, "logs --tail 1 backend", "first_backend", "Testing mode")

    else:
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

    # In swarm mode multiple services are not allowed
    if SWARM_MODE:
        exec_command(
            capfd,
            "logs --tail 1 backend frontend",
            "Error: Got unexpected extra argument (frontend)",
        )
    else:
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

    # With multiple services logs are not timestamped
    if not SWARM_MODE:
        # Multiple services are not supported in swarm mode
        exec_command(
            capfd,
            "logs --tail 10 frontend backend",
            # Logs are prefixed because more than one service is shown
            "backend_1      | Testing mode",
            # "backend_1       | Development mode",
            "frontend_1     | Merging files...",
        )
