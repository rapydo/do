"""
This module will test the cronjobs installed on the backend container
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


def test_cronjobs(capfd: Capture, faker: Faker) -> None:

    project = random_project_name(faker)
    create_project(
        capfd=capfd,
        name=project,
        auth="postgres",
        frontend="no",
    )
    init_project(capfd, "-e CRONTAB_ENABLE=1 -e HEALTHCHECK_INTERVAL=1s")
    start_registry(capfd)
    pull_images(capfd)
    start_project(capfd)

    exec_command(capfd, "status")

    exec_command(
        capfd,
        "logs --tail 50 backend",
        # Logs are not prefixed because only one service is shown
        "Found no cronjob to be enabled, skipping crontab setup",
        "Testing mode",
    )

    with open(f"projects/{project}/backend/cron/hello-world.cron", "w+") as f:
        f.write("* * * * * echo 'Hello world' >> /var/log/cron.log 2>&1\n")
        f.write("\n")

    exec_command(
        capfd,
        "-e CRONTAB_ENABLE=1 restart --force",
        "Stack restarted",
    )

    if SWARM_MODE:
        time.sleep(5)

    exec_command(
        capfd,
        "logs --tail 50 backend",
        # Logs are not prefixed because only one service is shown
        # "Testing mode",
        "Enabling cron...",
        "Cron enabled",
        # this is the output of crontab -l that verifies the cronjob installation
        "* * * * * echo 'Hello world'",
    )
