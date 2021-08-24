from controller import log
from controller.app import Application
from controller.deploy.compose_v2 import Compose


@Application.app.command(help="Restart modified running containers")
def restart() -> None:
    Application.get_controller().controller_init()

    dc = Compose(Application.data.files)
    dc.start_containers(Application.data.services)

    log.info("Stack restarted")
