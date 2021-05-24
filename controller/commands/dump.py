from controller import COMPOSE_FILE, log
from controller.app import Application
from controller.compose import Compose


@Application.app.command(help="Dump current config into docker compose YAML")
def dump() -> None:
    Application.get_controller().controller_init()

    dc = Compose(Application.data.files)
    compose_config = dc.config()
    dc.dump_config(compose_config, COMPOSE_FILE, Application.data.active_services)

    log.info("Config dump: {}", COMPOSE_FILE)
