import typer
from glom import glom

from controller.app import Application, Configuration
from controller.swarm import Swarm

# scaling should be a "Multiple Value"


@Application.app.command(help="[SWARM] Scale the number of containers for one service")
def scale(
    scaling: str = typer.Argument(..., help="scale SERVICE to NUM_REPLICA")
) -> None:
    Application.get_controller().controller_init()

    options = scaling.split("=")
    if len(options) != 2:
        scale_var = f"DEFAULT_SCALE_{scaling.upper()}"
        nreplicas = glom(
            Configuration.specs, f"variables.env.{scale_var}", default=None
        )
        if nreplicas is None:
            hints = f"You can also set a {scale_var} variable in your .projectrc file"

            Application.exit(
                "Please specify how to scale: SERVICE=NUM_REPLICA\n\n{}", hints
            )
        service = scaling
    else:
        service, nreplicas = options

    if nreplicas is None or (isinstance(nreplicas, str) and not nreplicas.isnumeric()):
        # str() is needed because nreplicas can be None
        Application.exit("Invalid number of replicas: {}", str(nreplicas))

    swarm = Swarm()
    swarm.scale(service, int(nreplicas))
