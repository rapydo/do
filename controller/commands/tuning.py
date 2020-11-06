import os
from enum import Enum

import typer

from controller import log
from controller.app import Application, Configuration
from controller.compose import Compose
from controller.utilities import system


class Services(str, Enum):
    neo4j = "neo4j"
    postgres = "postgres"
    backend = "backend"


@Application.app.command(help="Tuning suggestion for a service")
def tuning(
    service: Services = typer.Argument(..., help="Service name"),
    cpu: int = typer.Option(None, "--cpu", help="Force the amount of cpus", min=1),
    ram: int = typer.Option(None, "--ram", help="Force the amount of ram", min=1),
) -> None:
    Application.get_controller().controller_init()

    service = service.value

    if not cpu:
        cpu = os.cpu_count() or 1

    if not ram:
        ram = os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES")

    log.info("Number of CPU(s): {}", cpu)
    log.info("Amount of RAM: {}", system.bytes_to_str(ram))

    log.info("Suggested settings:")

    if service == Services.neo4j:

        dc = Compose(files=Application.data.files)

        running_containers = dc.get_running_containers(Configuration.project)
        container_is_running = service in running_containers

        command = f"neo4j-admin memrec --memory {ram}"

        if container_is_running:
            dc.exec_command(service, command=command, disable_tty=True)
        else:
            dc.create_volatile_container(service, command=command)

        # output = temporary_stream.getvalue().split("\\")
        # print(output)
        # Don't allocate more than 31g of heap,
        # since this will disable pointer compression, also known as "compressed oops",
        # in the JVM and make less effective use of the heap.
        # heap = min(ram * 0.4, 31 * GB)
        # print(f"NEO4J_HEAP_SIZE: {bytes_to_str(heap)}")
        # print(f"NEO4J_PAGECACHE_SIZE: {bytes_to_str(ram * 0.3)}")
        log.info("Use 'dbms.memory.heap.max_size' as NEO4J_HEAP_SIZE")
        log.info("Use 'dbms.memory.pagecache.size' as NEO4J_PAGECACHE_SIZE")
        log.info(
            "Keep enough free memory for lucene indexes "
            "(check size reported in the output, if any)"
        )

    if service == Services.postgres:

        # Something like 25% of available RAM
        print(f"POSTGRES_SHARED_BUFFERS: {system.bytes_to_str(ram * 0.25)}")
        # Something like 75% of available RAM
        print(f"POSTGRES_EFFECTIVE_CACHE_SIZE: {system.bytes_to_str(ram * 0.75)}")
        # Something like 1/16 of RAM
        print(f"POSTGRES_MAINTENANCE_WORK_MEM: {system.bytes_to_str(ram * 0.0625)}")
        # Set as the number of core (and not more).
        print(f"POSTGRES_MAX_WORKER_PROCESSES: {cpu}")

    if service == Services.backend:
        print(f"GUNICORN_MAX_NUM_WORKERS: {1 + 2 * cpu}")
