"""
Show tuning suggestions for a service
"""
import os
from enum import Enum

import typer

from controller import log, print_and_exit
from controller.app import Application
from controller.commands import TUNING_MODULES
from controller.utilities import system

# Enum() expects a string, tuple, list or dict literal as the second argument
# https://github.com/python/mypy/issues/5317
SupportedServices = Enum(  # type: ignore
    "SupportedServices", {name: name for name in sorted(TUNING_MODULES.keys())}
)


@Application.app.command(help="Tuning suggestions for a service")
def tuning(
    service: SupportedServices = typer.Argument(..., help="Service name"),
    cpu: int = typer.Option(None, "--cpu", help="Force the amount of cpus", min=1),
    ram: int = typer.Option(None, "--ram", help="Force the amount of ram", min=1),
) -> None:
    Application.print_command(
        Application.serialize_parameter("--cpu", cpu, IF=cpu),
        Application.serialize_parameter("--ram", ram, IF=ram),
        Application.serialize_parameter("", service),
    )
    Application.get_controller().controller_init()

    if not cpu:
        cpu = os.cpu_count() or 1

    if not ram:
        ram = os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES")

    log.info("Number of CPU(s): {}", cpu)
    log.info("Amount of RAM: {}", system.bytes_to_str(ram))

    log.info("Suggested settings:")

    module = TUNING_MODULES.get(service.value)

    if not module:  # pragma: no cover
        print_and_exit(f"{service.value} misconfiguration, module not found")

    module.tuning(ram, cpu)
