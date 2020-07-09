import typer
from glom import glom

from controller import EXTENDED_PROJECT_DISABLED
from controller.app import Application
from controller.commands.create import create_project


@Application.app.command(help="Upgrade a project by re-applying the templates")
def upgrade(
    path: str = typer.Option(
        ..., "--path", help="path of file to be upgraded", show_default=False,
    ),
):

    frontend = glom(Application.data.conf_vars, "env.FRONTEND_FRAMEWORK", default=None)
    auth = glom(Application.data.conf_vars, "env.AUTH_SERVICE", default=None)
    extend = glom(Application.data.conf_vars, "env.EXTENDED_PROJECT", default=None)

    if extend == EXTENDED_PROJECT_DISABLED:
        extend = None

    force = path is not None
    auto = path is not None

    create_project(
        project_name=Application.data.project,
        auth=auth,
        frontend=frontend,
        services=Application.data.services,
        extend=extend,
        force_current=True,
        force=force,
        auto=auto,
        path=path,
    )
