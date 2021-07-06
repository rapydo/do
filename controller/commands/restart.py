from controller import SWARM_MODE, log
from controller.app import Application
from controller.deploy.compose import Compose
from controller.deploy.swarm import Swarm


@Application.app.command(help="Restart running containers")
def restart() -> None:
    Application.get_controller().controller_init()

    if SWARM_MODE:
        swarm = Swarm()
        log.info("Restarting services:")
        for service in Application.data.services:
            swarm.restart(service)
    else:
        dc = Compose(files=Application.data.files)
        dc.start_containers(Application.data.services, force_recreate=True)

    log.info("Stack restarted")
