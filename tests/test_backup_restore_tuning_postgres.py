"""
This module test the backup and restore commands + tuning postgres
"""
import os

from tests import TemporaryRemovePath, create_project, exec_command, random_project_name


def test_all(capfd, fake):

    create_project(
        capfd=capfd,
        name=random_project_name(fake),
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
        " normal_user | User",
    )

    exec_command(
        capfd,
        "backup postgres",
        "Starting backup on postgres...",
        "Backup completed: data/backup/postgres/",
    )
    exec_command(
        capfd,
        "backup invalid",
        "invalid choice: invalid. (choose from neo4j, postgres)",
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

    with TemporaryRemovePath("data/backup"):
        exec_command(
            capfd,
            "restore postgres",
            "No backup found, the following folder "
            "does not exist: data/backup/postgres",
        )

    dfolder = "data/backup/postgres"
    with TemporaryRemovePath(dfolder):
        exec_command(
            capfd,
            "restore postgres",
            f"No backup found, the following folder does not exist: {dfolder}",
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
        " normal_user | User",
    )
    # 2) Modify such data
    exec_command(
        capfd,
        f'{psql} "update role SET description=name"\'',
    )
    exec_command(
        capfd,
        f'{psql} "select name, description from role"\'',
        " normal_user | normal_user",
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
        " normal_user | User",
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
