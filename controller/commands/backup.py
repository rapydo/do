import typer

from controller import log
from controller.app import Application


@Application.app.command(help="Execute a backup of one service")
def backup(service: str = typer.Argument(..., help="Service name")):
    Application.controller.controller_init()

    log.warning("Backup on {} is not implemented", service)
