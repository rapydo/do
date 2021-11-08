from faker import Faker

from controller import colors
from tests import (
    Capture,
    create_project,
    exec_command,
    init_project,
    pull_images,
    random_project_name,
    service_verify,
    start_project,
    start_registry,
)


def test_tuning(capfd: Capture, faker: Faker) -> None:

    create_project(
        capfd=capfd,
        name=random_project_name(faker),
        auth="neo4j",
        services=["postgres"],
        frontend="no",
    )
    init_project(capfd)

    start_registry(capfd)

    exec_command(
        capfd,
        "tuning neo4j",
        f"image, execute {colors.RED}rapydo pull neo4j",
    )

    pull_images(capfd)

    # TEMPORARY DISABLED REF736
    # Tuning command with neo4j container OFF
    # exec_command(
    #     capfd,
    #     "tuning neo4j",
    #     "Number of CPU(s): ",
    #     "Amount of RAM: ",
    #     "Suggested settings:",
    #     "Use 'dbms.memory.heap.max_size' as NEO4J_HEAP_SIZE",
    #     "Use 'dbms.memory.pagecache.size' as NEO4J_PAGECACHE_SIZE",
    #     "Memory settings recommendation from neo4j-admin memrec:",
    #     "Based on the above, the following memory settings are recommended:",
    #     "dbms.memory.heap.initial_size=",
    #     "dbms.memory.heap.max_size=",
    #     "dbms.memory.pagecache.size=",
    #     "Total size of lucene indexes in all databases:",
    #     "Total size of data and native indexes in all databases:",
    # )

    start_project(capfd)

    service_verify(capfd, "neo4j")
    service_verify(capfd, "sqlalchemy")

    exec_command(
        capfd,
        "tuning backend",
        "Number of CPU(s): ",
        "Amount of RAM: ",
        "Suggested settings:",
        "GUNICORN_MAX_NUM_WORKERS",
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
