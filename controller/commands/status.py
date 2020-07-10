from controller.app import Application
from controller.compose import Compose


@Application.app.command(help="Show current containers status")
def status():
    Application.controller.controller_init()

    dc = Compose(files=Application.data.files)
    dc.command("ps", {"-q": None, "--services": None, "--quiet": False, "--all": False})
