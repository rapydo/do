from pathlib import Path

import typer
from glom import glom

from controller import EXTENDED_PROJECT_DISABLED
from controller.app import Application, Configuration
from controller.commands.create import create_project
from controller.project import NO_FRONTEND


@Application.app.command(help="Upgrade a project by re-applying the templates")
def upgrade(
    path: Path = typer.Option(
        ...,
        "--path",
        help="path of file to be upgraded",
        show_default=False,
    ),
) -> None:

    Application.print_command(
        Application.serialize_parameter("--path", path, IF=path),
    )

    Application.get_controller().controller_init()

    frontend = glom(
        Configuration.specs, "variables.env.FRONTEND_FRAMEWORK", default=NO_FRONTEND
    )
    auth = glom(
        Configuration.specs, "variables.env.AUTH_SERVICE", default="NO_AUTHENTICATION"
    )
    extend = glom(Configuration.specs, "variables.env.EXTENDED_PROJECT", default=None)

    if extend == EXTENDED_PROJECT_DISABLED:
        extend = None

    force = path is not None
    auto = path is not None

    create_project(
        project_name=Configuration.project,
        auth=auth,
        frontend=frontend,
        services=Application.data.services,
        extend=extend,
        force_current=True,
        force=force,
        auto=auto,
        add_optionals=True,
        path=path,
    )
