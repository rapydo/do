"""
This module will test the volatile command
"""
# import signal

from faker import Faker

from controller import __version__, colors
from tests import (  # signal_handler,
    Capture,
    create_project,
    exec_command,
    init_project,
    pull_images,
    random_project_name,
    start_registry,
)


def test_volatile(capfd: Capture, faker: Faker) -> None:

    create_project(
        capfd=capfd,
        name=random_project_name(faker),
        auth="postgres",
        frontend="angular",
    )
    init_project(capfd)

    start_registry(capfd)

    exec_command(
        capfd,
        "volatile backend",
        "Volatile command is replaced by rapydo run --debug backend",
    )

    exec_command(
        capfd,
        "run --debug backend",
        f"Missing rapydo/backend:{__version__} image, add {colors.RED}--pull{colors.RESET} option",
    )

    pull_images(capfd)
    # start_project(capfd)

    # exec_command(
    #     capfd,
    #     "run --debug backend --command hostname",
    #     "Bind for 0.0.0.0:8080 failed: port is already allocated",
    # )

    # exec_command(
    #     capfd,
    #     "remove",
    #     "Stack removed",
    # )

    exec_command(
        capfd,
        "run backend --command hostname",
        "Can't specify a command if debug mode is OFF",
    )

    exec_command(
        capfd,
        "run backend --command hostname --user developer",
        "Can't specify a user if debug mode is OFF",
    )

    # TEMPORARY DISABLED 662
    # exec_command(
    #     capfd,
    #     "run --debug backend --command hostname",
    #     "backend-server",
    # )

    # exec_command(
    #     capfd,
    #     "run --debug backend --command whoami",
    #     "root",
    # )
    # exec_command(
    #     capfd,
    #     "run --debug backend -u developer --command whoami",
    #     "Please remember that users in volatile containers are not mapped on current ",
    #     "developer",
    # )
    # exec_command(
    #     capfd,
    #     "run --debug backend -u invalid --command whoami",
    #     "Error response from daemon:",
    #     "unable to find user invalid:",
    #     "no matching entries in passwd file",
    # )
