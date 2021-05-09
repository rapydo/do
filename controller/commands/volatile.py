import typer

from controller import log
from controller.app import Application
from controller.compose import Compose


@Application.app.command(help="Create a single-command container")
def volatile(
    service: str = typer.Argument(
        ...,
        help="Service name",
        autocompletion=Application.autocomplete_allservice,
    ),
    command: str = typer.Argument(
        "bash", help="UNIX command to be executed on selected running service"
    ),
    user: str = typer.Option(
        None,
        "--user",
        "-u",
        help="User existing in selected service",
        show_default=False,
    ),
) -> None:
    Application.get_controller().controller_init()

    if user:
        log.warning(
            "Please remember that users in volatile containers are not mapped "
            "on current uid and gid. "
            "You should avoid to write or modify files on volumes"
        )

    # One command container (NOT executing on a running one)
    dc = Compose(files=Application.data.files)
    dc.create_volatile_container(service, command=command, user=user)
