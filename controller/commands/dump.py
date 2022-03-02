"""
Dump the current configuration into a docker compose YAML file
"""
from controller import COMPOSE_FILE, log
from controller.app import Application, Configuration
from controller.deploy.docker import Docker


@Application.app.command(help="Dump current config into docker compose YAML")
def dump() -> None:

    Application.print_command()
    Application.get_controller().controller_init()

    docker = Docker()
    docker.compose.dump_config(
        Application.data.services, v1_compatibility=not Configuration.swarm_mode
    )

    log.info("Config dump: {}", COMPOSE_FILE)
