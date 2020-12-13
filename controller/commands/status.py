from controller.app import Application
from controller.compose import Compose


@Application.app.command(help="Show current containers status")
def status() -> None:
    Application.get_controller().controller_init()

    dc = Compose(files=Application.data.files)
    dc.command("ps", {"--quiet": False, "--services": None, "--all": False})
