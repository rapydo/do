import typer

from controller.app import Application
from controller.compose import Compose


@Application.app.command(help="Test if service is reachable from the backend")
def verify(
    service: str = typer.Argument(
        ..., help="Service name", autocompletion=Application.autocomplete_service
    )
):
    Application.controller.controller_init()

    # Verify one service connection (inside backend)
    dc = Compose(files=Application.data.files)
    command = f"restapi verify --services {service}"

    try:
        return dc.exec_command("backend", command=command)
    except SystemExit:
        pass
