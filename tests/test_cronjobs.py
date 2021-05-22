"""
This module will test the cronjobs installed on the backend container
"""
import time

from faker import Faker

from tests import Capture, create_project, exec_command, random_project_name


def test_cronjobs(capfd: Capture, faker: Faker) -> None:

    project = random_project_name(faker)
    create_project(
        capfd=capfd,
        name=project,
        auth="postgres",
        frontend="no",
        init=True,
        pull=True,
        start=False,
    )

    exec_command(
        capfd,
        "-e CRONTAB_ENABLE=1 start",
        "docker-compose command: 'up'",
        "Stack started",
    )

    # Add some delay to wait the container to start
    time.sleep(5)

    exec_command(
        capfd,
        "logs -s backend --tail 50 --no-color",
        "docker-compose command: 'logs'",
        # Logs are not prefixed because only one service is shown
        "Found no cronjob to be enabled, skipping crontab setup",
        "Testing mode",
    )

    with open(f"projects/{project}/backend/cron/hello-world.cron", "w+") as f:
        f.write("* * * * * echo 'Hello world' >> /var/log/cron.log 2>&1\n")
        f.write("\n")

    # Restart to enable to cronjobs
    exec_command(
        capfd,
        "-s backend restart",
        "Stack restarted",
    )

    exec_command(
        capfd,
        "logs -s backend --tail 50 --no-color",
        "docker-compose command: 'logs'",
        # Logs are not prefixed because only one service is shown
        # "Testing mode",
        "Enabling cron...",
        "Cron enabled",
        # this is the output of crontab -l that verifies the cronjob installation
        "* * * * * echo 'Hello world'",
    )

    exec_command(capfd, "remove --all", "Stack removed")
