"""
This module will test the volatile command
"""
import signal

from tests import create_project, exec_command, random_project_name, signal_handler


def test_volatile(capfd, fake):

    create_project(
        capfd=capfd,
        name=random_project_name(fake),
        auth="postgres",
        frontend="angular",
        init=True,
        pull=True,
        start=True,
    )

    exec_command(
        capfd,
        "volatile backend hostname",
        "Bind for 0.0.0.0:8080 failed: port is already allocated",
    )

    signal.signal(signal.SIGALRM, signal_handler)
    signal.alarm(4)
    exec_command(
        capfd,
        "-s backend start --no-detach",
        # "REST API backend server is ready to be launched",
        "Time is up",
    )

    # This is because after start --no-detach the container in still in exited status
    exec_command(
        capfd,
        "volatile backend hostname",
        "Bind for 0.0.0.0:8080 failed: port is already allocated",
    )

    exec_command(
        capfd,
        "remove --all",
        "Stack removed",
    )

    exec_command(
        capfd,
        "volatile backend --command hostname",
        "Deprecated use of --command",
    )
    exec_command(
        capfd,
        "volatile backend --command 'hostname --short'",
        "Deprecated use of --command",
    )

    exec_command(
        capfd,
        "volatile backend hostname",
        "backend-server",
    )

    exec_command(
        capfd,
        "volatile backend whoami",
        "root",
    )
    exec_command(
        capfd,
        "volatile backend -u developer whoami",
        "Please remember that users in volatile containers are not mapped on current ",
        "developer",
    )
    exec_command(
        capfd,
        "volatile backend -u invalid whoami",
        "Error response from daemon:",
        "unable to find user invalid:",
        "no matching entries in passwd file",
    )

    signal.signal(signal.SIGALRM, signal_handler)
    signal.alarm(4)
    exec_command(
        capfd,
        "volatile maintenance",
        # "Maintenance server is up and waiting for connections",
        "Time is up",
    )
