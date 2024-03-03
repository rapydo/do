"""
This module will test the backup and restore commands on rabbitMQ
"""
import os
import time

from faker import Faker

from controller import BACKUP_DIR, colors
from controller.app import Configuration
from tests import (
    Capture,
    TemporaryRemovePath,
    create_project,
    exec_command,
    execute_outside,
    init_project,
    pull_images,
    random_project_name,
    service_verify,
    start_project,
    start_registry,
)


def test_all(capfd: Capture, faker: Faker) -> None:
    execute_outside(capfd, "backup rabbit")
    execute_outside(capfd, "restore rabbit")

    backup_folder = BACKUP_DIR.joinpath("rabbit")

    create_project(
        capfd=capfd,
        name=random_project_name(faker),
        auth="no",
        frontend="no",
        services=["rabbit"],
    )
    init_project(capfd)
    start_registry(capfd)

    exec_command(
        capfd,
        "backup rabbit",
        f"image, execute {colors.RED}rapydo pull rabbit",
    )
    exec_command(
        capfd,
        "restore rabbit",
        f"image, execute {colors.RED}rapydo pull rabbit",
    )

    pull_images(capfd)
    start_project(capfd)

    exec_command(capfd, "status")
    service_verify(capfd, "rabbitmq")

    # Just some delay extra delay, rabbit is a slow starter
    time.sleep(5)

    # NOTE: q = rabbitmq.__name__ is just to have a fixed name to be used to test the
    # queue without the need to introdure further nested " or '
    query_queue = "shell backend \"/usr/bin/python3 -c 'from restapi.connectors import rabbitmq; q = rabbitmq.__name__; r = rabbitmq.get_instance();print(q, r.queue_exists(q));'\""  # noqa
    create_queue = "shell backend \"/usr/bin/python3 -c 'from restapi.connectors import rabbitmq; q = rabbitmq.__name__; r = rabbitmq.get_instance(); r.create_queue(q);'\""  # noqa
    delete_queue = "shell backend \"/usr/bin/python3 -c 'from restapi.connectors import rabbitmq; q = rabbitmq.__name__; r = rabbitmq.get_instance(); r.delete_queue(q);'\""  # noqa

    exec_command(capfd, query_queue, "restapi.connectors.rabbitmq False")

    exec_command(
        capfd,
        create_queue,
    )

    exec_command(capfd, query_queue, "restapi.connectors.rabbitmq True")

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
        "Restarting services in 20 seconds...",
        "Restarting services in 10 seconds...",
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
        "Invalid value for",
        "is not one of 'neo4j', 'postgres', 'rabbit', 'redis'",
    )

    exec_command(capfd, "remove", "Stack removed")

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

    exec_command(capfd, "start backend rabbit")

    # Just some delay extra delay, rabbit is a slow starter
    if Configuration.swarm_mode:
        time.sleep(20)
    else:
        time.sleep(10)

    exec_command(
        capfd,
        delete_queue,
    )

    exec_command(capfd, query_queue, "restapi.connectors.rabbitmq False")

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

    with TemporaryRemovePath(BACKUP_DIR):
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

    exec_command(capfd, "remove")
    # 3) restore the dump
    exec_command(
        capfd,
        f"restore rabbit {rabbit_dump_file}",
        "Starting restore on rabbit...",
        f"Restore from data/backup/rabbit/{rabbit_dump_file} completed",
    )

    exec_command(capfd, "start", "Stack started")
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
        f"Restore from data/backup/rabbit/{rabbit_dump_file} completed",
        "Restarting services in 20 seconds...",
        "Restarting services in 10 seconds...",
    )

    # Wait rabbit to completely startup
    service_verify(capfd, "rabbitmq")

    exec_command(capfd, query_queue, "restapi.connectors.rabbitmq True")
