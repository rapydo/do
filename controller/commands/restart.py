from controller import log
from controller.app import Application
from controller.compose import Compose


@Application.app.command(help="Restart running containers")
def restart():
    Application.get_controller().controller_init()

    options = {"SERVICE": Application.data.services}

    dc = Compose(files=Application.data.files)
    dc.command("restart", options)

    log.info("Stack restarted")
