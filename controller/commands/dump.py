from controller import COMPOSE_FILE, SWARM_MODE, log
from controller.app import Application
from controller.deploy.docker import Docker


@Application.app.command(help="Dump current config into docker compose YAML")
def dump() -> None:

    Application.print_command()
    Application.get_controller().controller_init()

    docker = Docker()
    docker.compose.dump_config(
        Application.data.services, v1_compatibility=not SWARM_MODE
    )

    log.info("Config dump: {}", COMPOSE_FILE)
