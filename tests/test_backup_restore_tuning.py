"""
This module list will test the backup and restore commands + tuning
on both postgres and neo4j databases
"""
import os

from tests import TemporaryRemovePath, create_project, exec_command


def test_all(capfd):

    create_project(
        capfd=capfd,
        name="first",
        auth="postgres",
        frontend="no",
        services=["neo4j"],
        extra="--env CUSTOMVAR1=mycustomvalue --env CUSTOMVAR2=mycustomvalue",
        init=True,
    )
    exec_command(
        capfd,
        "start",
        "docker-compose command: 'up'",
        "Stack started",
    )

    exec_command(capfd, "verify --no-tty sqlalchemy", "Service sqlalchemy is reachable")
    exec_command(capfd, "verify --no-tty neo4j", "Service neo4j is reachable")

    # This will initialize postgres
    exec_command(capfd, "shell --no-tty backend 'restapi init'")
    # And this will also initialize neo4j (what a trick!)
    # Temporary change AUTH_SERVICE from postgres to neo4j
    exec_command(capfd, "-e AUTH_SERVICE=neo4j -s backend start")
    exec_command(capfd, "shell --no-tty backend 'restapi init'")
    # Restore correct AUTH_SERVICE
    exec_command(capfd, "-s backend start")

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
        "backup neo4j",
        "Starting backup on neo4j...",
        "Backup completed: data/backup/neo4j/",
    )

    exec_command(capfd, "-s neo4j start")

    exec_command(
        capfd,
        "backup postgres",
        "The backup procedure requires postgres running, please start your stack",
    )

    # Restore command
    exec_command(
        capfd, "restore neo4j", "Please specify one of the following backup:", ".dump"
    )
    exec_command(
        capfd,
        "restore postgres",
        "Please specify one of the following backup:",
        ".sql.gz",
    )
    exec_command(
        capfd,
        "restore neo4j invalid",
        "Invalid backup file, data/backup/neo4j/invalid does not exist",
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

        exec_command(
            capfd,
            "restore neo4j",
            "No backup found, the following folder "
            "does not exist: data/backup/neo4j",
        )

    with TemporaryRemovePath("data/backup/neo4j"):
        exec_command(
            capfd,
            "restore neo4j",
            "No backup found, the following folder does not exist: data/backup/neo4j",
        )
        exec_command(
            capfd,
            "restore postgres",
            "Please specify one of the following backup:",
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

    files = os.listdir("data/backup/postgres")
    files = [f for f in files if f.endswith(".sql.gz")]
    files.sort()
    postgres_dump_file = files[-1]

    # You should somehow verify output from (or similar):
    # command = "bin/cypher-shell \"match (u: User) return u.email\""

    cypher = "shell --no-tty neo4j 'bin/cypher-shell"
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

    # Postgres restore not allowed if container is not running
    exec_command(
        capfd,
        f"restore postgres {postgres_dump_file}",
        "The restore procedure requires postgres running, please start your stack",
    )

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

    exec_command(
        capfd,
        "restart",
        "Stack restarted",
    )

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

    psql = "shell --no-tty postgres 'psql -U sqluser -d SQL_API -c"
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

    # This is postponed from one hundred lines above
    # 4) verify data match again point 1 (restore completed)
    exec_command(
        capfd,
        f'{cypher} "match (r: Role) return r.name, r.description"\'',
        '"normal_user", "User"',
    )

    # Test tuning neo4j with container already running
    exec_command(
        capfd,
        "tuning neo4j",
        "Number of CPU(s): ",
        "Amount of RAM: ",
        "Suggested settings:",
        "Use 'dbms.memory.heap.max_size' as NEO4J_HEAP_SIZE",
        "Use 'dbms.memory.pagecache.size' as NEO4J_PAGECACHE_SIZE",
    )
