from controller.app import Application
from controller.swarm import Swarm


@Application.app.command(help="[SWARM] Show current containers status")
def status() -> None:
    Application.get_controller().controller_init()

    swarm = Swarm()

    swarm.status()
