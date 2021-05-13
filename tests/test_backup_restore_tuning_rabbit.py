"""
This module will test the backup and restore commands on rabbitMQ
+ (tuning not implemented)
"""
import os
import time
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

    backup_folder = Path("data/backup/rabbit")

    create_project(
        capfd=capfd,
        name=random_project_name(faker),
        auth="postgres",
        frontend="no",
        services=["rabbit"],
        init=True,
        pull=True,
        start=True,
    )

    exec_command(capfd, "verify --no-tty rabbitmq", "Service rabbitmq is reachable")

    # # This will initialize rabbit
    # exec_command(capfd, "shell --no-tty backend 'restapi init'")

    # Just some delay extra delay, rabbit is a slow starter
    time.sleep(5)

    # Verify the initialization
    query_queue = "shell --no-tty backend \"/usr/bin/python3 -c 'from restapi.connectors import rabbitmq; r = rabbitmq.get_instance();print('QUEUE EXISTS =', r.queue_exists('blabla'));'\""
    create_queue = "shell --no-tty backend \"/usr/bin/python3 -c 'from restapi.connectors import rabbitmq; r = rabbitmq.get_instance(); r.create_queue('blabla');'\""
    delete_queue = "shell --no-tty backend \"/usr/bin/python3 -c 'from restapi.connectors import rabbitmq; r = rabbitmq.get_instance(); r.delete_queue('blabla');'\""

    exec_command(capfd, query_queue, "QUEUE EXISTS = False")

    exec_command(
        capfd,
        create_queue,
    )

    exec_command(capfd, query_queue, "QUEUE EXISTS = True")

    # Backup command
    exec_command(
        capfd,
        "backup rabbit",
        "RabbitMQ is running and the backup will temporary stop it. "
        "If you want to continue add --force flag",
    )
    exec_command(
        capfd,
        "backup rabbit --force --restart backend",
        "Starting backup on rabbit...",
        "Backup completed: data/backup/rabbit/",
    )
    # This is to verify that --force restarted rabbit
    exec_command(
        capfd,
        "backup rabbit",
        "RabbitMQ is running and the backup will temporary stop it. "
        "If you want to continue add --force flag",
    )

    exec_command(
        capfd,
        "backup invalid",
        "invalid choice: invalid. (choose from neo4j, postgres, mariadb, rabbit)",
    )

    exec_command(
        capfd,
        "stop",
        "Stack stopped",
    )

    exec_command(
        capfd,
        "backup rabbit",
        "Starting backup on rabbit...",
        "Backup completed: data/backup/rabbit/",
    )

    # Test backup retention
    exec_command(
        capfd,
        "backup rabbit --max 999 --dry-run",
        "Dry run mode is enabled",
        "Found 2 backup files, maximum not reached",
        "Starting backup on rabbit...",
        "Backup completed: data/backup/rabbit/",
    )
    # Verify that due to dry run, no backup is executed
    exec_command(
        capfd,
        "backup rabbit --max 999 --dry-run",
        "Dry run mode is enabled",
        "Found 2 backup files, maximum not reached",
        "Starting backup on rabbit...",
        "Backup completed: data/backup/rabbit/",
    )

    exec_command(
        capfd,
        "backup rabbit --max 1 --dry-run",
        "Dry run mode is enabled",
        "deleted because exceeding the max number of backup files (1)",
        "Starting backup on rabbit...",
        "Backup completed: data/backup/rabbit/",
    )
    # Verify that due to dry run, no backup is executed
    exec_command(
        capfd,
        "backup rabbit --max 1 --dry-run",
        "Dry run mode is enabled",
        "deleted because exceeding the max number of backup files (1)",
        "Starting backup on rabbit...",
        "Backup completed: data/backup/rabbit/",
    )

    # Create an additional backup to the test deletion (now backups are 3)
    exec_command(
        capfd,
        "backup rabbit",
        "Starting backup on rabbit...",
        "Backup completed: data/backup/rabbit/",
    )

    # Save the current number of backup files
    number_of_backups = len(list(backup_folder.glob("*")))

    # Verify the deletion
    exec_command(
        capfd,
        "backup rabbit --max 1",
        "deleted because exceeding the max number of backup files (1)",
        "Starting backup on rabbit...",
        "Backup completed: data/backup/rabbit/",
    )

    # Now the number of backups should be reduced by 1 (i.e. +1 -2)
    assert len(list(backup_folder.glob("*"))) == number_of_backups - 1

    # Verify that --max ignores files without the date pattern
    backup_folder.joinpath("xyz").touch(exist_ok=True)
    backup_folder.joinpath("xyz.ext").touch(exist_ok=True)
    backup_folder.joinpath("2020_01").touch(exist_ok=True)
    backup_folder.joinpath("2020_01_01").touch(exist_ok=True)
    backup_folder.joinpath("2020_01_01-01").touch(exist_ok=True)
    backup_folder.joinpath("2020_01_01-01_01").touch(exist_ok=True)
    backup_folder.joinpath("2020_01_01-01_01_01").touch(exist_ok=True)
    backup_folder.joinpath("9999_01_01-01_01_01.bak").touch(exist_ok=True)
    backup_folder.joinpath("2020_99_01-01_01_01.bak").touch(exist_ok=True)
    backup_folder.joinpath("2020_01_99-01_01_01.bak").touch(exist_ok=True)
    backup_folder.joinpath("2020_01_01-99_01_01.bak").touch(exist_ok=True)
    backup_folder.joinpath("2020_01_01-01_99_01.bak").touch(exist_ok=True)
    backup_folder.joinpath("2020_01_01-01_01_99.bak").touch(exist_ok=True)

    exec_command(
        capfd,
        "backup rabbit --max 999 --dry-run",
        "Dry run mode is enabled",
        # Still finding 2, all files above are ignore because not matching the pattern
        "Found 2 backup files, maximum not reached",
        "Starting backup on rabbit...",
        "Backup completed: data/backup/rabbit/",
    )

    exec_command(capfd, "-s rabbit start")

    # Probably a sleep is needed here

    exec_command(
        capfd,
        delete_queue,
    )

    exec_command(capfd, query_queue, "QUEUE EXISTS = False")

    # Restore command
    exec_command(
        capfd,
        "restore rabbit",
        "Please specify one of the following backup:",
        ".tar.gz",
    )

    exec_command(
        capfd,
        "restore rabbit invalid",
        "Invalid backup file, data/backup/rabbit/invalid does not exist",
    )

    with TemporaryRemovePath(Path("data/backup")):
        exec_command(
            capfd,
            "restore rabbit",
            "No backup found, the following folder "
            "does not exist: data/backup/rabbit",
        )

    with TemporaryRemovePath(backup_folder):
        exec_command(
            capfd,
            "restore rabbit",
            f"No backup found, the following folder does not exist: {backup_folder}",
        )

        os.mkdir("data/backup/rabbit")

        exec_command(
            capfd,
            "restore rabbit",
            "No backup found, data/backup/rabbit is empty",
        )

        open("data/backup/rabbit/test.gz", "a").close()

        exec_command(
            capfd,
            "restore rabbit",
            "No backup found, data/backup/rabbit is empty",
        )

        open("data/backup/rabbit/test.tar.gz", "a").close()

        exec_command(
            capfd,
            "restore rabbit",
            "Please specify one of the following backup:",
            "test.tar.gz",
        )

        os.remove("data/backup/rabbit/test.gz")
        os.remove("data/backup/rabbit/test.tar.gz")

    # Test restore on rabbit (required rabbit to be down)
    files = os.listdir("data/backup/rabbit")
    files = [f for f in files if f.endswith(".tar.gz")]
    files.sort()
    rabbit_dump_file = files[-1]

    exec_command(capfd, "-s rabbit remove")
    # 3) restore the dump
    exec_command(
        capfd,
        f"restore rabbit {rabbit_dump_file}",
        "Starting restore on rabbit...",
        "Done: ",
        f"Restore from data/backup/rabbit/{rabbit_dump_file} completed",
    )

    exec_command(capfd, "-s rabbit start")
    # 4) verify data match again point 1 (restore completed)
    # postponed because rabbit needs time to start...

    exec_command(
        capfd,
        f"restore rabbit {rabbit_dump_file}",
        "RabbitMQ is running and the restore will temporary stop it.",
        "If you want to continue add --force flag",
    )

    exec_command(
        capfd,
        f"restore rabbit {rabbit_dump_file} --force --restart backend",
        "Starting restore on rabbit...",
        "Done: ",
        f"Restore from data/backup/rabbit/{rabbit_dump_file} completed",
    )

    # Wait rabbit to completely startup
    exec_command(capfd, "verify --no-tty rabbitmq", "Service rabbitmq is reachable")

    exec_command(capfd, query_queue, "QUEUE EXISTS = True")

    exec_command(capfd, "remove --all", "Stack removed")
