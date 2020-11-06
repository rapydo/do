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
    # Deprecated since 0.8
    old_command: str = typer.Option(
        None,
        "--command",
        "-c",
        help="[DEPRECATED] UNIX command to be executed",
        show_default=False,
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

    # Deprecated since 0.8
    if old_command:
        if " " in old_command:
            cmd = f'"{old_command}"'
        else:
            cmd = old_command
        log.warning(
            "Deprecated use of --command, use: rapydo shell {} {}", service, cmd
        )
        command = old_command

    if user:
        log.warning(
            "Please remember that users in volatile containers are not mapped "
            "on current uid and gid. "
            "You should avoid to write or modify files on volumes"
        )

    # One command container (NOT executing on a running one)
    dc = Compose(files=Application.data.files)
    dc.create_volatile_container(service, command=command, user=user)
