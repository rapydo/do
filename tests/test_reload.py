"""
This module will test the reload command
"""
from faker import Faker

from tests import (
    Capture,
    create_project,
    exec_command,
    execute_outside,
    init_project,
    pull_images,
    random_project_name,
    start_project,
    start_registry,
    wait_until,
)


def test_base(capfd: Capture, faker: Faker) -> None:

    execute_outside(capfd, "reload")

    create_project(
        capfd=capfd,
        name=random_project_name(faker),
        auth="postgres",
        frontend="no",
    )
    init_project(capfd)

    exec_command(capfd, "reload", "No service reloaded")
    exec_command(capfd, "reload backend", "No service reloaded")
    exec_command(capfd, "reload invalid", "No such service: invalid")
    exec_command(capfd, "reload backend invalid", "No such service: invalid")

    start_registry(capfd)
    pull_images(capfd)

    start_project(capfd)

    exec_command(capfd, "reload backend", "Not implemented yet")

    exec_command(capfd, "reload postgres", "Not implemented yet")

    exec_command(capfd, "shell backend -u root 'rm /usr/local/bin/reload'")

    exec_command(
        capfd, "reload backend", "Service backend does not support the reload command"
    )

    exec_command(capfd, "remove", "Stack removed")


def test_reload_dev(capfd: Capture, faker: Faker) -> None:
    create_project(
        capfd=capfd,
        name=random_project_name(faker),
        auth="postgres",
        frontend="angular",
        services=[
            "neo4j",
            "mysql",
            "redis",
            # temporary disabled rabbit
            # "rabbit",
            "celery",
            "flower",
            "mongo",
            "ftp",
            "fail2ban",
        ],
    )
    init_project(capfd)

    pull_images(capfd)

    start_project(capfd)

    wait_until(capfd, "logs --tail 10 backend", "Testing mode")

    # For each support service verify:
    #   1) a start line in the logs
    #   2) the container is not re-created after the command
    #   3) the start line in the logs is printed again
    #   4) some more deep check based on the service?
    #      For example API is loading a change in the code?
    exec_command(capfd, "reload backend", "Not implemented yet")
    exec_command(capfd, "reload frontend", "Not implemented yet")
    exec_command(capfd, "reload postgres", "Not implemented yet")
    exec_command(
        capfd, "reload mariadb", "Service mariadb does not support the reload command"
    )
    exec_command(
        capfd, "reload redis", "Service redis does not support the reload command"
    )
    # Temporary disabled rabbit
    # exec_command(capfd, "reload rabbit", "Not implemented yet")
    exec_command(capfd, "reload celery", "Not implemented yet")
    exec_command(capfd, "reload flower", "Not implemented yet")
    exec_command(capfd, "reload mongodb", "Not implemented yet")
    exec_command(capfd, "reload ftp", "Not implemented yet")
    exec_command(capfd, "reload fail2ban", "Not implemented yet")

    exec_command(capfd, "remove", "Stack removed")


def test_reload_prod(capfd: Capture, faker: Faker) -> None:
    create_project(
        capfd=capfd,
        name=random_project_name(faker),
        auth="postgres",
        frontend="angular",
        services=[
            "neo4j",
            "mysql",
            "redis",
            # temporary disabled rabbit
            # "rabbit",
            "celery",
            "flower",
            "mongo",
            "ftp",
            "fail2ban",
        ],
    )

    exec_command(
        capfd,
        "--prod init -f",
        "Created default .projectrc file",
        "Project initialized",
    )

    pull_images(capfd)

    start_project(capfd)

    wait_until(capfd, "logs --tail 10 backend", "Testing mode")

    exec_command(capfd, "reload backend", "Not implemented yet")
    exec_command(capfd, "reload frontend", "Not implemented yet")
    exec_command(capfd, "reload postgres", "Not implemented yet")
    exec_command(
        capfd, "reload mariadb", "Service mariadb does not support the reload command"
    )
    exec_command(
        capfd, "reload redis", "Service redis does not support the reload command"
    )
    # temporary disabled rabbit
    # exec_command(capfd, "reload rabbit", "Not implemented yet")
    exec_command(capfd, "reload celery", "Not implemented yet")
    exec_command(capfd, "reload flower", "Not implemented yet")
    exec_command(capfd, "reload mongodb", "Not implemented yet")
    exec_command(capfd, "reload ftp", "Not implemented yet")
    exec_command(capfd, "reload fail2ban", "Not implemented yet")

    exec_command(capfd, "remove", "Stack removed")
