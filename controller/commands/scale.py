import typer
from glom import glom

from controller.app import Application, Configuration
from controller.compose import Compose

# scaling should be a "Multiple Value"


@Application.app.command(help="Scale the number of containers for one service")
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
            hints = "You can also set a {} variable in your .projectrc file".format(
                scale_var
            )
            Application.exit(
                "Please specify how to scale: SERVICE=NUM_REPLICA\n\n{}", hints
            )
        service = scaling
        scaling = f"{service}={nreplicas}"
    else:
        service, nreplicas = options

    if isinstance(nreplicas, str) and not nreplicas.isnumeric():
        Application.exit("Invalid number of replicas: {}", nreplicas)

    dc = Compose(files=Application.data.files)
    dc.start_containers([service], scale=[scaling], skip_dependencies=True)
