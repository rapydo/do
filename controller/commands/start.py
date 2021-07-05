from controller import SWARM_MODE, log
from controller.app import Application, Configuration
from controller.deploy.builds import verify_available_images
from controller.deploy.compose import Compose
from controller.deploy.swarm import Swarm


@Application.app.command(help="Start services for this configuration")
def start() -> None:
    Application.get_controller().controller_init()

    if SWARM_MODE and Configuration.services_list is not None:
        Application.exit("The start command no longer supports -s/--services option")

    if Configuration.excluded_services_list is not None:
        Application.exit(
            "The start command no longer supports -S/--skip-services option"
        )

    verify_available_images(
        Application.data.services,
        Application.data.compose_config,
        Application.data.base_services,
    )

    if SWARM_MODE:
        swarm = Swarm()
        swarm.deploy()
    else:
        dc = Compose(files=Application.data.files)
        dc.start_containers(Application.data.services, force_recreate=False)

    log.info("Stack started")
