import os

from controller import log
from controller.templating import Templating

templating = Templating()


def create_endpoint(project_scaffold, name):
    log.warning("Endpoint creation not implemented yet")
    # template_name = "endpoint_template"
    # path = project_scaffold.p_path("backend", "apis")


def create_task(project_scaffold, name):
    template_name = "task_template"
    path = project_scaffold.p_path("backend", "tasks")
    path = os.path.join(path, f"{name}.py")

    if os.path.exists(path):
        log.exit("{} already exists", path)

    template = templating.get_template(template_name, {"name": name})

    templating.save_template(path, template, force=False)

    log.info("Task created: {}", path)


def create_component(project_scaffold, name):
    log.warning("Component creation not implemented yet")
    # template_name = "component_template"


def create_service(project_scaffold, name):
    log.warning("Service creation not implemented yet")
    # template_name = "service_template"


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
