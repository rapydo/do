"""
This module will test the backup and restore commands + tuning neo4j
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

    backup_folder = Path("data/backup/neo4j")

    create_project(
        capfd=capfd,
        name=random_project_name(faker),
        auth="neo4j",
        frontend="no",
        init=True,
        pull=True,
        start=True,
    )

    exec_command(capfd, "verify --no-tty neo4j", "Service neo4j is reachable")

    # This will initialize neo4j
    exec_command(capfd, "shell --no-tty backend 'restapi init'")

    # Just some delay extra delay. restapi init alone not always is enough...
    time.sleep(5)

    # Verify the initialization
    cypher = "shell --no-tty neo4j 'bin/cypher-shell"
    exec_command(
        capfd,
        f'{cypher} "match (r: Role) return r.name, r.description"\'',
        '"normal_user", "User"',
    )

    # Backup command
    exec_command(
        capfd,
        "backup neo4j",
        "Neo4j is running and the backup will temporary stop it. "
        "If you want to continue add --force flag",
    )
    exec_command(
        capfd,
        "backup neo4j --force --restart backend --restart rabbit",
        "Starting backup on neo4j...",
        "Backup completed: data/backup/neo4j/",
    )
    # This is to verify that --force restarted neo4j
    exec_command(
        capfd,
        "backup neo4j",
        "Neo4j is running and the backup will temporary stop it. "
        "If you want to continue add --force flag",
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
        "backup neo4j",
        "Starting backup on neo4j...",
        "Backup completed: data/backup/neo4j/",
    )

    # Test backup retention
    exec_command(
        capfd,
        "backup neo4j --max 999 --dry-run",
        "Dry run mode is enabled",
        "Found 2 backup files, maximum not reached",
        "Starting backup on neo4j...",
        "Backup completed: data/backup/neo4j/",
    )
    # Verify that due to dry run, no backup is executed
    exec_command(
        capfd,
        "backup neo4j --max 999 --dry-run",
        "Dry run mode is enabled",
        "Found 2 backup files, maximum not reached",
        "Starting backup on neo4j...",
        "Backup completed: data/backup/neo4j/",
    )

    exec_command(
        capfd,
        "backup neo4j --max 1 --dry-run",
        "Dry run mode is enabled",
        "deleted because exceeding the max number of backup files (1)",
        "Starting backup on neo4j...",
        "Backup completed: data/backup/neo4j/",
    )
    # Verify that due to dry run, no backup is executed
    exec_command(
        capfd,
        "backup neo4j --max 1 --dry-run",
        "Dry run mode is enabled",
        "deleted because exceeding the max number of backup files (1)",
        "Starting backup on neo4j...",
        "Backup completed: data/backup/neo4j/",
    )

    # Create an additional backup to the test deletion (now backups are 3)
    exec_command(
        capfd,
        "backup neo4j",
        "Starting backup on neo4j...",
        "Backup completed: data/backup/neo4j/",
    )

    # Save the current number of backup files
    number_of_backups = len(list(backup_folder.glob("*")))

    # Verify the deletion
    exec_command(
        capfd,
        "backup neo4j --max 1",
        "deleted because exceeding the max number of backup files (1)",
        "Starting backup on neo4j...",
        "Backup completed: data/backup/neo4j/",
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
        "backup neo4j --max 999 --dry-run",
        "Dry run mode is enabled",
        # Still finding 2, all files above are ignore because not matching the pattern
        "Found 2 backup files, maximum not reached",
        "Starting backup on neo4j...",
        "Backup completed: data/backup/neo4j/",
    )

    exec_command(capfd, "-s neo4j start")

    # Restore command
    exec_command(
        capfd, "restore neo4j", "Please specify one of the following backup:", ".dump"
    )

    exec_command(
        capfd,
        "restore neo4j invalid",
        "Invalid backup file, data/backup/neo4j/invalid does not exist",
    )

    with TemporaryRemovePath(Path("data/backup")):
        exec_command(
            capfd,
            "restore neo4j",
            "No backup found, the following folder "
            "does not exist: data/backup/neo4j",
        )

    with TemporaryRemovePath(backup_folder):
        exec_command(
            capfd,
            "restore neo4j",
            f"No backup found, the following folder does not exist: {backup_folder}",
        )

        os.mkdir("data/backup/neo4j")

        exec_command(
            capfd,
            "restore neo4j",
            "No backup found, data/backup/neo4j is empty",
        )

        open("data/backup/neo4j/test.gz", "a").close()

        exec_command(
            capfd,
            "restore neo4j",
            "No backup found, data/backup/neo4j is empty",
        )

        open("data/backup/neo4j/test.dump", "a").close()

        exec_command(
            capfd,
            "restore neo4j",
            "Please specify one of the following backup:",
            "test.dump",
        )

        os.remove("data/backup/neo4j/test.gz")
        os.remove("data/backup/neo4j/test.dump")

    # Test restore on neo4j (required neo4j to be down)
    files = os.listdir("data/backup/neo4j")
    files = [f for f in files if f.endswith(".dump")]
    files.sort()
    neo4j_dump_file = files[-1]

    # Here we test the restore procedure:
    # 1) verify some data in the database
    exec_command(
        capfd,
        f'{cypher} "match (r: Role) return r.name, r.description"\'',
        '"normal_user", "User"',
    )

    # 2) Modify such data
    exec_command(capfd, f'{cypher} "match (r: Role) SET r.description = r.name"\'')
    exec_command(
        capfd,
        f'{cypher} "match (r: Role) return r.name, r.description"\'',
        '"normal_user", "normal_user"',
    )
    exec_command(capfd, "-s neo4j remove")
    # 3) restore the dump
    exec_command(
        capfd,
        f"restore neo4j {neo4j_dump_file}",
        "Starting restore on neo4j...",
        "Done: ",
        f"Restore from data/backup/neo4j/{neo4j_dump_file} completed",
    )

    # Tuning command with neo4j container OFF
    exec_command(
        capfd,
        "tuning neo4j",
        "Number of CPU(s): ",
        "Amount of RAM: ",
        "Suggested settings:",
        "Use 'dbms.memory.heap.max_size' as NEO4J_HEAP_SIZE",
        "Use 'dbms.memory.pagecache.size' as NEO4J_PAGECACHE_SIZE",
        "Memory settings recommendation from neo4j-admin memrec:",
        "Based on the above, the following memory settings are recommended:",
        "dbms.memory.heap.initial_size=",
        "dbms.memory.heap.max_size=",
        "dbms.memory.pagecache.size=",
        "Total size of lucene indexes in all databases:",
        "Total size of data and native indexes in all databases:",
    )

    exec_command(capfd, "-s neo4j start")
    # 4) verify data match again point 1 (restore completed)
    # postponed because neo4j needs time to start...

    # Tuning command with neo4j container ON
    exec_command(
        capfd,
        "tuning neo4j",
        "Number of CPU(s): ",
        "Amount of RAM: ",
        "Suggested settings:",
        "Use 'dbms.memory.heap.max_size' as NEO4J_HEAP_SIZE",
        "Use 'dbms.memory.pagecache.size' as NEO4J_PAGECACHE_SIZE",
        "Memory settings recommendation from neo4j-admin memrec:",
        "Based on the above, the following memory settings are recommended:",
        "dbms.memory.heap.initial_size=",
        "dbms.memory.heap.max_size=",
        "dbms.memory.pagecache.size=",
        "Total size of lucene indexes in all databases:",
        "Total size of data and native indexes in all databases:",
    )

    exec_command(
        capfd,
        "tuning backend",
        "Number of CPU(s): ",
        "Amount of RAM: ",
        "Suggested settings:",
        "GUNICORN_MAX_NUM_WORKERS",
    )

    # exec_command(
    #     capfd,
    #     "restart",
    #     "Stack restarted",
    # )

    exec_command(
        capfd,
        f"restore neo4j {neo4j_dump_file}",
        "Neo4j is running and the restore will temporary stop it.",
        "If you want to continue add --force flag",
    )

    exec_command(
        capfd,
        f"restore neo4j {neo4j_dump_file} --force --restart backend",
        "Starting restore on neo4j...",
        "Done: ",
        f"Restore from data/backup/neo4j/{neo4j_dump_file} completed",
    )

    # Wait neo4j to completely startup
    exec_command(capfd, "verify --no-tty neo4j", "Service neo4j is reachable")

    # 4) verify data match again point 1 (restore completed)
    exec_command(
        capfd,
        f'{cypher} "match (r: Role) return r.name, r.description"\'',
        '"normal_user", "User"',
    )

    # # Test tuning neo4j with container already running
    # exec_command(
    #     capfd,
    #     "tuning neo4j",
    #     "Number of CPU(s): ",
    #     "Amount of RAM: ",
    #     "Suggested settings:",
    #     "Use 'dbms.memory.heap.max_size' as NEO4J_HEAP_SIZE",
    #     "Use 'dbms.memory.pagecache.size' as NEO4J_PAGECACHE_SIZE",
    # )

    exec_command(capfd, "remove --all", "Stack removed")
