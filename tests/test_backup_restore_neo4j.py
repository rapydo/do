"""
This module will test the backup and restore commands on neo4j
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

    execute_outside(capfd, "backup neo4j")
    execute_outside(capfd, "restore neo4j")

    backup_folder = BACKUP_DIR.joinpath("neo4j")

    create_project(
        capfd=capfd,
        name=random_project_name(faker),
        auth="neo4j",
        frontend="no",
    )
    init_project(capfd)
    start_registry(capfd)

    exec_command(
        capfd,
        "backup neo4j",
        f"image, execute {colors.RED}rapydo pull neo4j",
    )
    exec_command(
        capfd,
        "restore neo4j",
        f"image, execute {colors.RED}rapydo pull neo4j",
    )

    pull_images(capfd)
    start_project(capfd)

    service_verify(capfd, "neo4j")

    # This will initialize neo4j
    exec_command(capfd, "shell backend 'restapi init'")

    time.sleep(20)
    # Just some delay extra delay. restapi init alone not always is enough...
    if Configuration.swarm_mode:
        time.sleep(30)

    # Verify the initialization
    cypher = "shell neo4j 'bin/cypher-shell"
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
        "Restarting services in 20 seconds...",
        "Restarting services in 10 seconds...",
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
        "Invalid value for",
        "is not one of 'neo4j', 'postgres', 'rabbit', 'redis'",
    )

    exec_command(capfd, "remove", "Stack removed")

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

    exec_command(capfd, "start", "Stack started")

    # Just some delay extra delay, neo4j is a slow starter
    time.sleep(20)

    # Restore command
    exec_command(
        capfd, "restore neo4j", "Please specify one of the following backup:", ".dump"
    )

    exec_command(
        capfd,
        "restore neo4j invalid",
        "Invalid backup file, data/backup/neo4j/invalid does not exist",
    )

    with TemporaryRemovePath(BACKUP_DIR):
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

    time.sleep(20)

    # Here we test the restore procedure:
    # 1) verify some data in the database
    exec_command(
        capfd,
        f'{cypher} "match (r: Role) return r.name, r.description"\'',
        '"normal_user", "User"',
    )

    # 2) Modify the data
    exec_command(capfd, f'{cypher} "match (r: Role) SET r.description = r.name"\'')
    exec_command(
        capfd,
        f'{cypher} "match (r: Role) return r.name, r.description"\'',
        '"normal_user", "normal_user"',
    )
    exec_command(capfd, "remove")

    # 3) restore the dump
    exec_command(
        capfd,
        f"restore neo4j {neo4j_dump_file}",
        "Starting restore on neo4j...",
        "Done: ",
        f"Restore from data/backup/neo4j/{neo4j_dump_file} completed",
    )

    exec_command(capfd, "start", "Stack started")

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
        "Restarting services in 20 seconds...",
        "Restarting services in 10 seconds...",
    )

    # Wait neo4j to completely startup
    service_verify(capfd, "neo4j")

    # 4) verify data match again point 1 (restore completed)
    exec_command(
        capfd,
        f'{cypher} "match (r: Role) return r.name, r.description"\'',
        '"normal_user", "User"',
    )
