import typer
from glom import glom

from controller import print_and_exit
from controller.app import Application, Configuration
from controller.deploy.builds import verify_available_images
from controller.deploy.compose_v2 import Compose


@Application.app.command(help="Scale the number of containers for a service")
def scale(
    scaling: str = typer.Argument(..., help="scale SERVICE to NUM_REPLICA")
) -> None:

    Application.print_command(Application.serialize_parameter("", scaling))

    Application.get_controller().controller_init()

    options = scaling.split("=")
    if len(options) != 2:
        scale_var = f"DEFAULT_SCALE_{scaling.upper()}"
        nreplicas = glom(Configuration.specs, f"variables.env.{scale_var}", default="1")
        service = scaling
    else:
        service, nreplicas = options

    if isinstance(nreplicas, str) and not nreplicas.isnumeric():
        print_and_exit("Invalid number of replicas: {}", nreplicas)

    verify_available_images(
        [service],
        Application.data.compose_config,
        Application.data.base_services,
    )

    compose = Compose(Application.data.files)
    compose.start_containers([service], scales={service: int(nreplicas)})
