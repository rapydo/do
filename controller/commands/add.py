import os

from glom import glom

from controller import log
from controller.templating import Templating

templating = Templating()


def create_template(template_name, target_path, name, services, auth):

    if os.path.exists(target_path):
        log.exit("{} already exists", target_path)

    template = templating.get_template(
        template_name, {"name": name, "services": services, "auth": auth}
    )

    templating.save_template(target_path, template, force=False)


def create_endpoint(project_scaffold, name, services, auth):
    path = project_scaffold.p_path("backend", "apis")
    path = os.path.join(path, "{}.py".format(name))

    create_template("endpoint_template.py", path, name, services, auth)

    log.info("Endpoint created: {}", path)


def create_task(project_scaffold, name, services, auth):
    path = project_scaffold.p_path("backend", "tasks")
    path = os.path.join(path, "{}.py".format(name))

    create_template("task_template.py", path, name, services, auth)

    log.info("Task created: {}", path)


def create_component(project_scaffold, name, services, auth):
    path = project_scaffold.p_path("frontend", "app", "components", name)
    os.makedirs(path, exist_ok=True)

    cpath = os.path.join(path, "{}.ts".format(name))
    create_template("component_template.ts", cpath, name, services, auth)

    hpath = os.path.join(path, "{}.html".format(name))
    create_template("component_template.html", hpath, name, services, auth)

    log.info("Component created: {}", path)


def create_service(project_scaffold, name, services, auth):
    path = project_scaffold.p_path("frontend", "app", "services")
    os.makedirs(path, exist_ok=True)

    path = os.path.join(path, "{}.ts".format(name))

    create_template("service_template.ts", path, name, services, auth)

    log.info("Service created: {}", path)


def __call__(args, project_scaffold, services, conf_vars, **kwargs):

    functions = {
        "endpoint": create_endpoint,
        "task": create_task,
        "component": create_component,
        "service": create_service,
    }
    element_type = args.get("type")
    name = args.get("name")
    auth = glom(conf_vars, "env.AUTH_SERVICE", default=None)

    if element_type not in functions:
        log.exit(
            "Invalid type {}, please chose one of: {}",
            element_type,
            ", ".join(functions.keys()),
        )

    fn = functions.get(element_type)
    fn(project_scaffold, name, services, auth)
