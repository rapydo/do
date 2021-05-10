"""
This module test the backup and restore commands + tuning postgres
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

    backup_folder = Path("data/backup/postgres")

    create_project(
        capfd=capfd,
        name=random_project_name(faker),
        auth="postgres",
        frontend="no",
        init=True,
        pull=True,
        start=True,
    )

    exec_command(capfd, "verify --no-tty sqlalchemy", "Service sqlalchemy is reachable")

    # Just some delay extra delay. restapi init alone not always is enough...
    # time.sleep(5)

    # This will initialize postgres
    exec_command(capfd, "shell --no-tty backend 'restapi init'")

    # Verify the initialization
    psql = "shell --no-tty postgres 'psql -U sqluser -d SQL_API -c"
    exec_command(
        capfd,
        f'{psql} "select name, description from role"\'',
        " normal_user       | User",
    )

    exec_command(
        capfd,
        "backup postgres",
        "Starting backup on postgres...",
        "Backup completed: data/backup/postgres/",
    )

    # A second backup is needed to test backup retention
    exec_command(
        capfd,
        "backup postgres",
        "Starting backup on postgres...",
        "Backup completed: data/backup/postgres/",
    )

    # Test backup retention
    exec_command(
        capfd,
        "backup postgres --max 999 --dry-run",
        "Dry run mode is enabled",
        "Found 2 backup files, maximum not reached",
        "Starting backup on postgres...",
        "Backup completed: data/backup/postgres/",
    )
    # Verify that due to dry run, no backup is executed
    exec_command(
        capfd,
        "backup postgres --max 999 --dry-run",
        "Dry run mode is enabled",
        "Found 2 backup files, maximum not reached",
        "Starting backup on postgres...",
        "Backup completed: data/backup/postgres/",
    )

    exec_command(
        capfd,
        "backup postgres --max 1 --dry-run",
        "Dry run mode is enabled",
        "deleted because exceeding the max number of backup files (1)",
        "Starting backup on postgres...",
        "Backup completed: data/backup/postgres/",
    )
    # Verify that due to dry run, no backup is executed
    exec_command(
        capfd,
        "backup postgres --max 1 --dry-run",
        "Dry run mode is enabled",
        "deleted because exceeding the max number of backup files (1)",
        "Starting backup on postgres...",
        "Backup completed: data/backup/postgres/",
    )

    # Create an additional backup to the test deletion (now backups are 3)
    exec_command(
        capfd,
        "backup postgres",
        "Starting backup on postgres...",
        "Backup completed: data/backup/postgres/",
    )
    # Save the current number of backup files
    number_of_backups = len(list(backup_folder.glob("*")))

    # Verify the deletion
    exec_command(
        capfd,
        "backup postgres --max 1",
        "deleted because exceeding the max number of backup files (1)",
        "Starting backup on postgres...",
        "Backup completed: data/backup/postgres/",
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
    backup_folder.joinpath("2020_01_01-01_01_99.gz").touch(exist_ok=True)

    exec_command(
        capfd,
        "backup postgres --max 999 --dry-run",
        "Dry run mode is enabled",
        # Still finding 2, all files above are ignore because not matching the pattern
        "Found 2 backup files, maximum not reached",
        "Starting backup on postgres...",
        "Backup completed: data/backup/postgres/",
    )

    exec_command(
        capfd,
        "backup invalid",
        "invalid choice: invalid. (choose from neo4j, postgres, mariadb)",
    )

    exec_command(
        capfd,
        "stop",
        "Stack stopped",
    )

    exec_command(
        capfd,
        "backup postgres",
        "The backup procedure requires postgres running, please start your stack",
    )

    exec_command(
        capfd,
        "restore postgres",
        "Please specify one of the following backup:",
        ".sql.gz",
    )
    exec_command(
        capfd,
        "restore postgres invalid",
        "Invalid backup file, data/backup/postgres/invalid does not exist",
    )

    with TemporaryRemovePath(Path("data/backup")):
        exec_command(
            capfd,
            "restore postgres",
            "No backup found, the following folder "
            "does not exist: data/backup/postgres",
        )

    with TemporaryRemovePath(backup_folder):
        exec_command(
            capfd,
            "restore postgres",
            f"No backup found, the following folder does not exist: {backup_folder}",
        )

        os.mkdir("data/backup/postgres")

        exec_command(
            capfd,
            "restore postgres",
            "No backup found, data/backup/postgres is empty",
        )

        open("data/backup/postgres/test.sql.gz", "a").close()

        exec_command(
            capfd,
            "restore postgres",
            "Please specify one of the following backup:",
            "test.sql.gz",
        )

        os.remove("data/backup/postgres/test.sql.gz")

    files = os.listdir("data/backup/postgres")
    files = [f for f in files if f.endswith(".sql.gz")]
    files.sort()
    postgres_dump_file = files[-1]

    # Postgres restore not allowed if container is not running
    exec_command(
        capfd,
        f"restore postgres {postgres_dump_file}",
        "The restore procedure requires postgres running, please start your stack",
    )

    exec_command(
        capfd,
        "restart",
        "Stack restarted",
    )

    # Here we test the restore procedure:
    # 1) verify some data in the database
    exec_command(
        capfd,
        f'{psql} "select name, description from role"\'',
        " normal_user       | User",
    )
    # 2) Modify such data
    exec_command(
        capfd,
        f'{psql} "update role SET description=name"\'',
    )
    exec_command(
        capfd,
        f'{psql} "select name, description from role"\'',
        " normal_user       | normal_user",
    )
    # 3) restore the dump
    exec_command(
        capfd,
        f"restore postgres {postgres_dump_file}",
        "Starting restore on postgres...",
        "CREATE DATABASE",
        "ALTER DATABASE",
        f"Restore from data/backup/postgres/{postgres_dump_file} completed",
    )

    # 4) verify data match again point 1 (restore completed)
    exec_command(
        capfd,
        f'{psql} "select name, description from role"\'',
        " normal_user       | User",
    )

    exec_command(
        capfd,
        "tuning postgres",
        "Number of CPU(s): ",
        "Amount of RAM: ",
        "Suggested settings:",
        "POSTGRES_SHARED_BUFFERS",
        "POSTGRES_EFFECTIVE_CACHE_SIZE",
        "POSTGRES_MAINTENANCE_WORK_MEM",
        "POSTGRES_MAX_WORKER_PROCESSES",
    )
    exec_command(
        capfd,
        "tuning backend",
        "Number of CPU(s): ",
        "Amount of RAM: ",
        "Suggested settings:",
        "GUNICORN_MAX_NUM_WORKERS",
    )

    exec_command(capfd, "remove --all", "Stack removed")
