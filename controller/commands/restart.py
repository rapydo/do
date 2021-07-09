from controller import SWARM_MODE, log
from controller.app import Application, Configuration
from controller.deploy.compose import Compose
from controller.deploy.swarm import Swarm


@Application.app.command(help="Restart running containers")
def restart() -> None:
    Application.get_controller().controller_init()

    if SWARM_MODE:
        swarm = Swarm()
        if not swarm.stack_is_running(Configuration.project):
            Application.exit(
                "Stack {} is not running, deploy it with rapydo start",
                Configuration.project,
            )

        log.info("Restarting services:")
        for service in Application.data.services:
            swarm.restart(service)
    else:
        dc = Compose(files=Application.data.files)
        dc.start_containers(Application.data.services, force_recreate=True)

    log.info("Stack restarted")
