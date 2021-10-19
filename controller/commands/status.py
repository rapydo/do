from controller import SWARM_MODE
from controller.app import Application
from controller.deploy.compose_v2 import Compose
from controller.deploy.swarm import Swarm


@Application.app.command(help="Show current services status")
def status() -> None:

    Application.print_command()

    Application.get_controller().controller_init()

    if SWARM_MODE:
        swarm = Swarm()
        swarm.status()
    else:
        compose = Compose(Application.data.files)
        compose.status()
