from glom import glom

from controller import EXTENDED_PROJECT_DISABLED
from controller.commands.create import create

# from controller import log


def __call__(args, project, conf_vars, services, **kwargs):

    path = args.get("path", None)
    frontend = glom(conf_vars, "env.FRONTEND_FRAMEWORK", default=None)
    auth = glom(conf_vars, "env.AUTH_SERVICE", default=None)
    extend = glom(conf_vars, "env.EXTENDED_PROJECT", default=None)

    if extend == EXTENDED_PROJECT_DISABLED:
        extend = None

    create(
        project_name=project,
        auth=auth,
        frontend=frontend,
        services=services,
        extend=extend,
        force_current=True,
        path=path,
    )
