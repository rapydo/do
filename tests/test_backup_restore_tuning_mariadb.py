"""
This module test the backup and restore commands + tuning mariadb

NOT IMPLEMENTED
"""
import os
from pathlib import Path

from faker import Faker

from tests import (
    Capture,
    TemporaryRemovePath,
    create_project,
    exec_command,
    random_project_name,
)


def test_all(capfd: Capture, faker: Faker) -> None:

    backup_folder = Path("data/backup/mariadb")

    create_project(
        capfd=capfd,
        name=random_project_name(faker),
        auth="mysql",
        frontend="no",
        init=True,
        pull=True,
        start=True,
    )

    exec_command(capfd, "verify --no-tty mysql", "Service mysql is reachable")

    # Just some delay extra delay. restapi init alone not always is enough...
    # time.sleep(5)

    # This will initialize mariadb
    exec_command(capfd, "shell --no-tty backend 'restapi init'")

    exec_command(
        capfd,
        "backup mariadb",
        "Starting backup on mariadb...",
        # "Backup completed: data/backup/mariadb/",
        "Not implemented yet",
    )

    # A second backup is needed to test backup retention
    exec_command(
        capfd,
        "backup mariadb",
        "Starting backup on mariadb...",
        # "Backup completed: data/backup/mariadb/",
        "Not implemented yet",
    )

    exec_command(
        capfd,
        "stop",
        "Stack stopped",
    )

    exec_command(
        capfd,
        "backup mariadb",
        "The backup procedure requires mariadb running, please start your stack",
    )

    # TO BE RESTORED
    # exec_command(
    #     capfd,
    #     "restore mariadb",
    #     "Please specify one of the following backup:",
    #     ".sql.gz",
    # )
    exec_command(
        capfd,
        "restore mariadb invalid",
        "Invalid backup file, data/backup/mariadb/invalid does not exist",
    )

    with TemporaryRemovePath(Path("data/backup")):
        exec_command(
            capfd,
            "restore mariadb",
            "No backup found, the following folder "
            "does not exist: data/backup/mariadb",
        )

    with TemporaryRemovePath(backup_folder):
        exec_command(
            capfd,
            "restore mariadb",
            f"No backup found, the following folder does not exist: {backup_folder}",
        )

        os.mkdir("data/backup/mariadb")

        exec_command(
            capfd,
            "restore mariadb",
            "No backup found, data/backup/mariadb is empty",
        )

        open("data/backup/mariadb/test.sql.gz", "a").close()

        exec_command(
            capfd,
            "restore mariadb",
            "Please specify one of the following backup:",
            "test.sql.gz",
        )

        os.remove("data/backup/mariadb/test.sql.gz")

    # TO BE IMPLEMENTED
