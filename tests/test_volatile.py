"""
This module will test the volatile command
"""
# import signal

from faker import Faker

from tests import (  # signal_handler,
    Capture,
    create_project,
    exec_command,
    init_project,
    pull_images,
    random_project_name,
    start_project,
)


def test_volatile(capfd: Capture, faker: Faker) -> None:

    create_project(
        capfd=capfd,
        name=random_project_name(faker),
        auth="postgres",
        frontend="angular",
    )
    init_project(capfd)

    exec_command(
        capfd,
        "volatile backend",
        "image for backend service, execute rapydo pull",
    )

    pull_images(capfd)
    start_project(capfd)

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

    exec_command(
        capfd,
        "volatile maintenance",
        "image for proxy service, execute rapydo pull",
    )

    exec_command(
        capfd,
        "-s proxy -e ACTIVATE_PROXY=1 pull",
        "Base images pulled from docker hub",
    )

    # signal.signal(signal.SIGALRM, signal_handler)
    # signal.alarm(4)
    # exec_command(
    #     capfd,
    #     "volatile maintenance",
    #     # "Maintenance server is up and waiting for connections",
    #     "Time is up",
    # )
