"""
[DEPRECATED] Restart modified running containers
"""
import typer

from controller import RED, print_and_exit
from controller.app import Application


@Application.app.command(help="[DEPRECATED] Restart modified running containers")
def restart(
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Force services restart",
        show_default=False,
    ),
) -> None:

    # Deprecated since 2.2

    print_and_exit(
        "This command is no longer available "
        "\nIf you want to reload your services, use {} "
        "\nIf you want to recreated your containers, use {}",
        RED("rapydo reload"),
        RED("rapydo start --force"),
    )
