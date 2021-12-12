import typer

from controller import RED, log, print_and_exit
from controller.app import Application, Configuration
from controller.deploy.builds import verify_available_images
from controller.deploy.docker import Docker
from controller.deploy.swarm import Swarm


@Application.app.command(help="Update deployed services")
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

    swarm = Swarm()

    if not swarm.stack_is_running():
        print_and_exit(
            "Your stack is not running, deploy it with {command}",
            command=RED("rapydo start"),
        )

    log.info("Restarting services:")

    docker = Docker()
    docker.compose.dump_config(Application.data.services)
    swarm.deploy()

    if force:
        for service in Application.data.services:
            docker.client.service.update(
                f"{Configuration.project}_{service}", detach=True, force=True
            )

    log.info("Stack restarted")
