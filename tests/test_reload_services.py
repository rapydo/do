"""
This module will test the reload command
"""
import time

from faker import Faker

from controller import SWARM_MODE
from tests import (
    Capture,
    create_project,
    exec_command,
    init_project,
    pull_images,
    random_project_name,
    start_project,
    start_registry,
)


def test_reload_dev(capfd: Capture, faker: Faker) -> None:
    create_project(
        capfd=capfd,
        name=random_project_name(faker),
        auth="postgres",
        frontend="no",
        services=[
            "neo4j",
            "mysql",
            "redis",
            "rabbit",
            # temporary disabled celery and flower
            # "celery",
            # "flower",
            "mongo",
            "ftp",
            "fail2ban",
        ],
    )
    init_project(capfd)
    start_registry(capfd)

    pull_images(capfd)

    start_project(capfd)

    # To be improved, of course!!
    time.sleep(30)
    if SWARM_MODE:
        time.sleep(20)

    # For each support service verify:
    #   1) a start line in the logs
    #   2) the container is not re-created after the command
    #   3) the start line in the logs is printed again
    #   4) some more deep check based on the service?
    #      For example API is loading a change in the code?
    exec_command(capfd, "reload postgres", "Not implemented yet")
    exec_command(
        capfd, "reload mariadb", "Service mariadb does not support the reload command"
    )
    exec_command(
        capfd, "reload redis", "Service redis does not support the reload command"
    )
    exec_command(capfd, "reload rabbit", "Not implemented yet")
    # temporary disabled celery and flower
    # exec_command(capfd, "reload celery", "Not implemented yet")
    # exec_command(capfd, "reload flower", "Not implemented yet")
    exec_command(capfd, "reload mongodb", "Not implemented yet")
    exec_command(capfd, "reload ftp", "Not implemented yet")
    exec_command(capfd, "reload fail2ban", "Not implemented yet")

    exec_command(capfd, "remove", "Stack removed")

    if SWARM_MODE:
        exec_command(capfd, "remove registry", "Service registry removed")


def test_reload_prod(capfd: Capture, faker: Faker) -> None:
    create_project(
        capfd=capfd,
        name=random_project_name(faker),
        auth="postgres",
        frontend="no",
        services=[
            "neo4j",
            "mysql",
            "redis",
            "rabbit",
            # temporary disabled celery and flower
            # "celery",
            # "flower",
            "mongo",
            "ftp",
            "fail2ban",
        ],
    )

    init_project(capfd, " --prod ", "--force")

    start_registry(capfd)
    pull_images(capfd)

    start_project(capfd)

    # To be improved, of course!!
    time.sleep(30)
    if SWARM_MODE:
        time.sleep(20)

    exec_command(capfd, "reload postgres", "Not implemented yet")
    exec_command(
        capfd, "reload mariadb", "Service mariadb does not support the reload command"
    )
    exec_command(
        capfd, "reload redis", "Service redis does not support the reload command"
    )
    exec_command(capfd, "reload rabbit", "Not implemented yet")
    # temporary disabled celery and flower
    # exec_command(capfd, "reload celery", "Not implemented yet")
    # exec_command(capfd, "reload flower", "Not implemented yet")
    exec_command(capfd, "reload mongodb", "Not implemented yet")
    exec_command(capfd, "reload ftp", "Not implemented yet")
    exec_command(capfd, "reload fail2ban", "Not implemented yet")

    exec_command(capfd, "remove", "Stack removed")
