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

    return "{}{}".format(int(round(value, 0)), unit)


@Application.app.command(help="Tuning suggestion for a service")
def tuning(
    service: Services = typer.Argument(..., help="Service name"),
):
    Application.controller.controller_init()

    service = service.value

    cpu = os.cpu_count()
    ram = virtual_memory().total

    log.info("Number of CPU: {}", cpu)
    log.info("Amount of RAM: {}", bytes_to_str(ram))

    if service == Services.neo4j:

        log.critical("Not implemented yet")

    if service == Services.postgres:

        log.info("Suggested settings:")
        # Something like 25% of available RAM
        print("POSTGRES_SHARED_BUFFERS: {}".format(bytes_to_str(ram * 0.25)))
        # Something like 75% of available RAM
        print("POSTGRES_EFFECTIVE_CACHE_SIZE: {}".format(bytes_to_str(ram * 0.75)))
        # Something like 1/16 of RAM
        print("POSTGRES_MAINTENANCE_WORK_MEM: {}".format(bytes_to_str(ram * 0.0625)))
        # Set as the number of core (and not more).
        print(f"POSTGRES_MAX_WORKER_PROCESSES: {cpu}")
