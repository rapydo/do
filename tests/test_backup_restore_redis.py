"""
This module will test the backup and restore commands on Redis
"""
import os
from pathlib import Path

from faker import Faker

from controller import colors
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

    execute_outside(capfd, "backup redis")
    execute_outside(capfd, "restore redis")

    backup_folder = Path("data/backup/redis")

    create_project(
        capfd=capfd,
        name=random_project_name(faker),
        auth="no",
        frontend="no",
        services=["redis"],
    )
    init_project(capfd)
    start_registry(capfd)

    exec_command(
        capfd,
        "backup redis",
        f"image, execute {colors.RED}rapydo pull redis",
    )
    exec_command(
        capfd,
        "restore redis",
        f"image, execute {colors.RED}rapydo pull redis",
    )

    pull_images(capfd)
    start_project(capfd)

    exec_command(capfd, "status")
    service_verify(capfd, "redis")

    key = faker.pystr()
    value1 = faker.pystr()
    value2 = faker.pystr()
    # NOTE: q = redis.__name__ is just to have a fixed name to be used to test the
    # queue without the need to introdure further nested " or '
    get_key = f'shell redis "sh -c \'redis-cli --pass "$REDIS_PASSWORD" get {key}\'"'
    set_key1 = (
        f'shell redis "sh -c \'redis-cli --pass "$REDIS_PASSWORD" set {key} {value1}\'"'
    )
    set_key2 = (
        f'shell redis "sh -c \'redis-cli --pass "$REDIS_PASSWORD" set {key} {value2}\'"'
    )

    exec_command(
        capfd,
        set_key1,
    )

    exec_command(capfd, get_key, value1)

    # Backup command on a running Redis
    exec_command(
        capfd,
        "backup redis",
        "Starting backup on redis...",
        "Backup completed: data/backup/redis/",
    )

    exec_command(
        capfd,
        "backup invalid",
        "Invalid value for",
        "'invalid' is not one of 'neo4j', 'postgres', 'mariadb', 'rabbit', 'redis'",
    )

    exec_command(capfd, "remove", "Stack removed")

    # Backup command on a stopped Redis
    exec_command(
        capfd,
        "backup redis",
        "Starting backup on redis...",
        "Backup completed: data/backup/redis/",
    )

    # Test backup retention
    exec_command(
        capfd,
        "backup redis --max 999 --dry-run",
        "Dry run mode is enabled",
        "Found 2 backup files, maximum not reached",
        "Starting backup on redis...",
        "Backup completed: data/backup/redis/",
    )
    # Verify that due to dry run, no backup is executed
    exec_command(
        capfd,
        "backup redis --max 999 --dry-run",
        "Dry run mode is enabled",
        "Found 2 backup files, maximum not reached",
        "Starting backup on redis...",
        "Backup completed: data/backup/redis/",
    )

    exec_command(
        capfd,
        "backup redis --max 1 --dry-run",
        "Dry run mode is enabled",
        "deleted because exceeding the max number of backup files (1)",
        "Starting backup on redis...",
        "Backup completed: data/backup/redis/",
    )
    # Verify that due to dry run, no backup is executed
    exec_command(
        capfd,
        "backup redis --max 1 --dry-run",
        "Dry run mode is enabled",
        "deleted because exceeding the max number of backup files (1)",
        "Starting backup on redis...",
        "Backup completed: data/backup/redis/",
    )

    # Create an additional backup to the test deletion (now backups are 3)
    exec_command(
        capfd,
        "backup redis",
        "Starting backup on redis...",
        "Backup completed: data/backup/redis/",
    )

    # Save the current number of backup files
    number_of_backups = len(list(backup_folder.glob("*")))

    # Verify the deletion
    exec_command(
        capfd,
        "backup redis --max 1",
        "deleted because exceeding the max number of backup files (1)",
        "Starting backup on redis...",
        "Backup completed: data/backup/redis/",
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
        "backup redis --max 999 --dry-run",
        "Dry run mode is enabled",
        # Still finding 2, all files above are ignore because not matching the pattern
        "Found 2 backup files, maximum not reached",
        "Starting backup on redis...",
        "Backup completed: data/backup/redis/",
    )

    exec_command(capfd, "start backend redis")

    exec_command(
        capfd,
        set_key2,
    )

    exec_command(capfd, get_key, value2)

    # Restore command
    exec_command(
        capfd,
        "restore redis",
        "Please specify one of the following backup:",
        ".tar.gz",
    )

    exec_command(
        capfd,
        "restore redis invalid",
        "Invalid backup file, data/backup/redis/invalid does not exist",
    )

    with TemporaryRemovePath(Path("data/backup")):
        exec_command(
            capfd,
            "restore redis",
            "No backup found, the following folder "
            "does not exist: data/backup/redis",
        )

    with TemporaryRemovePath(backup_folder):
        exec_command(
            capfd,
            "restore redis",
            f"No backup found, the following folder does not exist: {backup_folder}",
        )

        os.mkdir("data/backup/redis")

        exec_command(
            capfd,
            "restore redis",
            "No backup found, data/backup/redis is empty",
        )

        open("data/backup/redis/test.gz", "a").close()

        exec_command(
            capfd,
            "restore redis",
            "No backup found, data/backup/redis is empty",
        )

        open("data/backup/redis/test.tar.gz", "a").close()

        exec_command(
            capfd,
            "restore redis",
            "Please specify one of the following backup:",
            "test.tar.gz",
        )

        os.remove("data/backup/redis/test.gz")
        os.remove("data/backup/redis/test.tar.gz")

    # Test restore on redis (required redis to be down)
    files = os.listdir("data/backup/redis")
    files = [f for f in files if f.endswith(".tar.gz")]
    files.sort()
    redis_dump_file = files[-1]

    exec_command(capfd, "remove redis")
    # 3) restore the dump
    exec_command(
        capfd,
        f"restore redis {redis_dump_file}",
        "Starting restore on redis...",
        f"Restore from data/backup/redis/{redis_dump_file} completed",
    )

    exec_command(capfd, "restart")
    # 4) verify data match again point 1 (restore completed)
    # postponed because redis needs time to start...

    exec_command(
        capfd,
        f"restore redis {redis_dump_file}",
        "Redis is running and the restore will temporary stop it.",
        "If you want to continue add --force flag",
    )

    exec_command(
        capfd,
        f"restore redis {redis_dump_file} --force --restart backend",
        "Starting restore on redis...",
        f"Restore from data/backup/redis/{redis_dump_file} completed",
    )

    # Wait redis to completely startup
    service_verify(capfd, "redis")

    exec_command(capfd, get_key, value1)
