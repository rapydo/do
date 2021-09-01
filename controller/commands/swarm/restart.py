import typer

from controller import RED, log, print_and_exit
from controller.app import Application, Configuration
from controller.deploy.compose_v2 import Compose as ComposeV2
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

    swarm = Swarm()

    if not swarm.stack_is_running(Configuration.project):
        print_and_exit(
            "Stack {} is not running, deploy it with {command}",
            Configuration.project,
            command=RED("rapydo start"),
        )

    Application.get_controller().controller_init()

    log.info("Restarting services:")

    compose = ComposeV2(Application.data.files)
    compose.dump_config(Application.data.services)
    swarm.deploy()

    if force:
        for service in Application.data.services:
            compose.docker.service.update(
                f"{Configuration.project}_{service}", detach=True, force=True
            )

    log.info("Stack restarted")
