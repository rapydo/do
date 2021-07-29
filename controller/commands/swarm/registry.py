# from typing import Optional, List, Tuple

from controller import log, print_and_exit
from controller.app import Application
from controller.deploy.compose import Compose
from controller.deploy.docker import Docker


@Application.app.command(help="Start the local registry [TEMPORARY COMMAND]")
def registry() -> None:

    Application.get_controller().controller_init()

    log.warning(
        "This is a temporary command and will probably be merged"
        " with interfaces and volatile commands in a near future"
    )

    docker = Docker()
    if docker.ping_registry(do_exit=False):
        registry = docker.get_registry()
        print_and_exit("The registry is already running at {}", registry)

    # Not implemented yet with compose v2
    compose = Compose(Application.data.files)
    # compose.docker.compose.up(detach=True)
    compose.start_containers(["registry"])
