from controller import SWARM_MODE, log
from controller.app import Application
from controller.deploy.builds import verify_available_images
from controller.deploy.compose import Compose
from controller.deploy.swarm import Swarm


@Application.app.command(help="Start services for this configuration")
def start() -> None:
    Application.get_controller().controller_init()

    for service in Application.data.services:
        if service not in Application.data.active_services:
            Application.exit("No such service: {}", service)

    verify_available_images(
        Application.data.services,
        Application.data.compose_config,
        Application.data.base_services,
    )

    if SWARM_MODE:

        swarm = Swarm()
        if Application.data.services != Application.data.active_services:
            if swarm.docker.stack.list():
                Application.exit("A stack is already running")

        swarm.deploy()
    else:
        dc = Compose(files=Application.data.files)
        dc.start_containers(Application.data.services, force_recreate=False)

    log.info("Stack started")
