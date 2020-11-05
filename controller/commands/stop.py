from controller import log
from controller.app import Application
from controller.compose import Compose


@Application.app.command(help="Stop running containers, but do not remove them")
def stop():
    Application.get_controller().controller_init()

    options = {"SERVICE": Application.data.services}

    dc = Compose(files=Application.data.files)
    dc.command("stop", options)

    log.info("Stack stopped")
