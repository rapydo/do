import typer

from controller import log
from controller.app import Application
from controller.deploy.builds import verify_available_images
from controller.deploy.docker import Docker


@Application.app.command(help="Restart modified running containers")
def restart(
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Force services restart",
        show_default=False,
    ),
) -> None:
    Application.print_command(
        Application.serialize_parameter("--force", force, IF=force),
    )
    Application.get_controller().controller_init()

    verify_available_images(
        Application.data.services,
        Application.data.compose_config,
        Application.data.base_services,
    )

    docker = Docker()
    docker.compose.start_containers(Application.data.services, force=force)

    log.info("Stack restarted")
