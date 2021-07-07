import typer
from glom import glom

from controller.app import Application, Configuration
from controller.deploy.builds import verify_available_images
from controller.deploy.compose import Compose

# scaling should be a "Multiple Value"


@Application.app.command(help="Scale the number of containers for one service")
def scale(
    scaling: str = typer.Argument(..., help="scale SERVICE to NUM_REPLICA")
) -> None:
    Application.get_controller().controller_init()

    options = scaling.split("=")
    if len(options) != 2:
        scale_var = f"DEFAULT_SCALE_{scaling.upper()}"
        nreplicas = glom(Configuration.specs, f"variables.env.{scale_var}", default="1")
        service = scaling
        scaling = f"{service}={nreplicas}"
    else:
        service, nreplicas = options

    if isinstance(nreplicas, str) and not nreplicas.isnumeric():
        Application.exit("Invalid number of replicas: {}", nreplicas)

    verify_available_images(
        [service],
        Application.data.compose_config,
        Application.data.base_services,
    )

    dc = Compose(files=Application.data.files)
    dc.start_containers([service], scale=[scaling], skip_dependencies=True)
