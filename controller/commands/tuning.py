import os
from enum import Enum

import typer
from psutil import virtual_memory

from controller import log
from controller.app import Application

GB = 1_073_741_824
MB = 1_048_576
KB = 1024


class Services(str, Enum):
    neo4j = "neo4j"
    postgres = "postgres"
    backend = "backend"


def bytes_to_str(value):

    if value >= GB:
        value /= GB
        unit = "GB"
    elif value >= MB:
        value /= MB
        unit = "MB"
    elif value >= KB:
        value /= KB
        unit = "KB"
    else:
        unit = ""

    return f"{int(round(value, 0))}{unit}"


@Application.app.command(help="Tuning suggestion for a service")
def tuning(
    service: Services = typer.Argument(..., help="Service name"),
):
    Application.controller.controller_init()

    service = service.value

    cpu = os.cpu_count()
    ram = virtual_memory().total

    log.info("Number of CPU(s): {}", cpu)
    log.info("Amount of RAM: {}", bytes_to_str(ram))

    log.info("Suggested settings:")

    if service == Services.neo4j:

        # Then add options to tests
        log.critical("Not implemented yet")

    if service == Services.postgres:

        # Something like 25% of available RAM
        print(f"POSTGRES_SHARED_BUFFERS: {bytes_to_str(ram * 0.25)}")
        # Something like 75% of available RAM
        print(f"POSTGRES_EFFECTIVE_CACHE_SIZE: {bytes_to_str(ram * 0.75)}")
        # Something like 1/16 of RAM
        print(f"POSTGRES_MAINTENANCE_WORK_MEM: {bytes_to_str(ram * 0.0625)}")
        # Set as the number of core (and not more).
        print(f"POSTGRES_MAX_WORKER_PROCESSES: {cpu}")

    if service == Services.backend:
        print(f"GUNICORN_MAX_NUM_WORKERS: {1 + 2 * cpu}")
