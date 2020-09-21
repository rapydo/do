import typer

from controller import log
from controller.app import Application


@Application.app.command(help="Execute diagnostic tools against a host")
def diagnostic(host: str = typer.Argument(..., help="Host to verified")):
    Application.controller.controller_init()

    log.critical("Command not implemented on host: {}", host)
