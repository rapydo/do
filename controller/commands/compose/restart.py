from controller import log
from controller.app import Application
from controller.deploy.compose import Compose


@Application.app.command(help="Restart running containers")
def restart() -> None:
    Application.get_controller().controller_init()

    dc = Compose(files=Application.data.files)
    dc.start_containers(Application.data.services, force_recreate=True)

    log.info("Stack restarted")
