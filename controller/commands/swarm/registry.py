# from typing import Optional, List, Tuple
import os

from controller import log, print_and_exit
from controller.app import Application, Configuration
from controller.deploy.compose import Compose
from controller.deploy.docker import Docker
from controller.templating import password


@Application.app.command(help="Start the local registry [TEMPORARY COMMAND]")
def registry() -> None:

    Configuration.FORCE_COMPOSE_ENGINE = True
    # @ symbol in secrets is not working
    # https://github.com/bitnami/charts/issues/1954
    # Other symbols like # and " also lead to configuration errors
    os.environ["REGISTRY_HTTP_SECRET"] = password(
        param_not_used="",
        length=96
        # , symbols="%*,-.=?[]^_~"
    )
    Application.get_controller().controller_init()

    Application.get_controller().check_placeholders(
        Application.data.compose_config, ["registry"]
    )

    log.warning(
        "This is a temporary command and will probably be merged"
        " with interfaces and volatile commands in a near future"
    )

    docker = Docker()
    if docker.ping_registry(do_exit=False):
        registry = docker.get_registry()
        print_and_exit("The registry is already running at {}", registry)

    compose = Compose(files=Application.data.files)
    # compose.start_containers(["registry"])
    compose.create_volatile_container("registry", detach=True)
