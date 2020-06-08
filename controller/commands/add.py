import os

from controller import log
from controller.templating import Templating

templating = Templating()


def create_template(template_name, target_path, name):

    if os.path.exists(target_path):
        log.exit("{} already exists", target_path)

    template = templating.get_template(template_name, {"name": name})

    templating.save_template(target_path, template, force=False)


def create_endpoint(project_scaffold, name):
    log.exit("Endpoint creation not implemented yet")
    path = project_scaffold.p_path("backend", "apis")

    create_template("endpoint_template", path, name)


def create_task(project_scaffold, name):
    path = project_scaffold.p_path("backend", "tasks")
    path = os.path.join(path, "{}.py".format(name))

    create_template("task_template", path, name)

    log.info("Task created: {}", path)


def create_component(project_scaffold, name):
    log.exit("Component creation not implemented yet")
    path = project_scaffold.p_path("frontend", "app", "components")

    create_template("component_template", path, name)


def create_service(project_scaffold, name):
    log.exit("Service creation not implemented yet")
    path = project_scaffold.p_path("frontend", "app", "services")

    create_template("service_template", path, name)


def __call__(args, project_scaffold, **kwargs):

    functions = {
        "endpoint": create_endpoint,
        "task": create_task,
        "component": create_component,
        "service": create_service,
    }
    element_type = args.get("type")
    name = args.get("name")

    if element_type not in functions:
        log.exit(
            "Invalid type {}, please chose one of: {}",
            element_type,
            ", ".join(functions.keys()),
        )

    fn = functions.get(element_type)
    fn(project_scaffold, name)
