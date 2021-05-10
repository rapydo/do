"""
This module test the backup and restore commands + (tuning not implemented) mariadb
"""
import os
from pathlib import Path

from faker import Faker

# from controller import log
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

    exec_command(capfd, "verify --no-tty sqlalchemy", "Service sqlalchemy is reachable")

    # Just some delay extra delay. restapi init alone not always is enough...
    # time.sleep(5)

    # This will initialize mariadb
    exec_command(capfd, "shell --no-tty backend 'restapi init'")

    def exec_query(query):

        command = 'shell --no-tty mariadb "'
        command += 'sh -c \'mysql -uroot -p"$MYSQL_ROOT_PASSWORD" -D"$MYSQL_DATABASE" '
        command += f'-e \\"{query};\\"'
        # This is to close the sh -c 'command'
        command += "'"
        # This is to close the shell "command"
        command += '"'

        return command

    # Verify the initialization
    exec_command(
        capfd,
        exec_query("select name, description from role"),
        "normal_user\tUser",
    )

    exec_command(
        capfd,
        "backup mariadb",
        "Starting backup on mariadb...",
        "Backup completed: data/backup/mariadb/",
    )

    # A second backup is needed to test backup retention
    exec_command(
        capfd,
        "backup mariadb",
        "Starting backup on mariadb...",
        "Backup completed: data/backup/mariadb/",
    )

    # Test backup retention
    exec_command(
        capfd,
        "backup mariadb --max 999 --dry-run",
        "Dry run mode is enabled",
        "Found 2 backup files, maximum not reached",
        "Starting backup on mariadb...",
        "Backup completed: data/backup/mariadb/",
    )
    # Verify that due to dry run, no backup is executed
    exec_command(
        capfd,
        "backup mariadb --max 999 --dry-run",
        "Dry run mode is enabled",
        "Found 2 backup files, maximum not reached",
        "Starting backup on mariadb...",
        "Backup completed: data/backup/mariadb/",
    )

    exec_command(
        capfd,
        "backup mariadb --max 1 --dry-run",
        "Dry run mode is enabled",
        "deleted because exceeding the max number of backup files (1)",
        "Starting backup on mariadb...",
        "Backup completed: data/backup/mariadb/",
    )
    # Verify that due to dry run, no backup is executed
    exec_command(
        capfd,
        "backup mariadb --max 1 --dry-run",
        "Dry run mode is enabled",
        "deleted because exceeding the max number of backup files (1)",
        "Starting backup on mariadb...",
        "Backup completed: data/backup/mariadb/",
    )

    # Create an additional backup to the test deletion (now backups are 3)
    exec_command(
        capfd,
        "backup mariadb",
        "Starting backup on mariadb...",
        "Backup completed: data/backup/mariadb/",
    )
    # Save the current number of backup files
    number_of_backups = len(list(backup_folder.glob("*")))

    # Verify the deletion
    exec_command(
        capfd,
        "backup mariadb --max 1",
        "deleted because exceeding the max number of backup files (1)",
        "Starting backup on mariadb...",
        "Backup completed: data/backup/mariadb/",
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
    backup_folder.joinpath("2020_01_01-01_01_99.tar").touch(exist_ok=True)
    backup_folder.joinpath("2020_01_01-01_01_99.tar.gz").touch(exist_ok=True)

    exec_command(
        capfd,
        "backup mariadb --max 999 --dry-run",
        "Dry run mode is enabled",
        # Still finding 2, all files above are ignore because not matching the pattern
        "Found 2 backup files, maximum not reached",
        "Starting backup on mariadb...",
        "Backup completed: data/backup/mariadb/",
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
        "backup mariadb",
        "The backup procedure requires mariadb running, please start your stack",
    )

    exec_command(
        capfd,
        "restore mariadb",
        "Please specify one of the following backup:",
        ".tar.gz",
    )
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

        open("data/backup/mariadb/test.tar.gz", "a").close()

        exec_command(
            capfd,
            "restore mariadb",
            "Please specify one of the following backup:",
            "test.tar.gz",
        )

        os.remove("data/backup/mariadb/test.tar.gz")

    files = os.listdir("data/backup/mariadb")
    files = [f for f in files if f.endswith(".tar.gz")]
    files.sort()
    mariadb_dump_file = files[-1]

    exec_command(
        capfd,
        "restart",
        "Stack restarted",
    )

    # Postgres restore not allowed if container is not running
    exec_command(
        capfd,
        f"restore mariadb {mariadb_dump_file}",
        "MariaDB is running and the restore will temporary stop it. "
        "If you want to continue add --force flag",
    )

    exec_command(
        capfd,
        "stop",
        "Stack stopped",
    )

    # Here we test the restore procedure:
    # 1) verify some data in the database
    exec_command(
        capfd,
        exec_query("select name, description from role"),
        "normal_user\tUser",
    )
    # 2) Modify such data
    exec_command(
        capfd,
        exec_query("update role SET description=name"),
    )
    exec_command(
        capfd,
        exec_query("select name, description from role"),
        "normal_user\tnormal_user",
    )
    # 3) restore the dump
    exec_command(
        capfd,
        f"restore mariadb {mariadb_dump_file}",
        "Starting restore on mariadb...",
        "Opening backup file",
        "Removing current datadir",
        "Restoring the backup",
        "...done",
        "completed OK!",
        "Removing the temporary uncompressed folder",
        f"Restore from data/backup/mariadb/{mariadb_dump_file} completed",
    )

    # 4) verify data match again point 1 (restore completed)
    exec_command(
        capfd,
        exec_query("select name, description from role"),
        "normal_user\tUser",
    )

    exec_command(capfd, "remove --all", "Stack removed")
