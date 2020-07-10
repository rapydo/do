import os
from enum import Enum

import typer
from glom import glom

from controller import log
from controller.app import Application, Configuration
from controller.templating import Templating

templating = Templating()


class ElementTypes(str, Enum):
    endpoint = "endpoint"
    task = "task"
    component = "component"
    service = "service"


@Application.app.command(help="Add a new element")
def add(
    element_type: ElementTypes = typer.Argument(
        ..., help="Type of element to be created"
    ),
    name: str = typer.Argument(..., help="Name to be assigned to the new element"),
):

    Application.controller.controller_init()

    functions = {
        "endpoint": create_endpoint,
        "task": create_task,
        "component": create_component,
        "service": create_service,
    }
    auth = glom(Configuration.specs, "variables.env.AUTH_SERVICE", default=None)

    fn = functions.get(element_type)

    fn(Application.project_scaffold, name, Application.data.services, auth)


def create_template(template_name, target_path, name, services, auth):

    if os.path.exists(target_path):
        log.exit("{} already exists", target_path)

    template = templating.get_template(
        template_name, {"name": name, "services": services, "auth": auth}
    )

    templating.save_template(target_path, template, force=False)


def create_endpoint(project_scaffold, name, services, auth):
    path = project_scaffold.p_path("backend", "apis")
    path = os.path.join(path, f"{name}.py")

    create_template("endpoint_template.py", path, name, services, auth)

    log.info("Endpoint created: {}", path)


def create_task(project_scaffold, name, services, auth):
    path = project_scaffold.p_path("backend", "tasks")
    path = os.path.join(path, f"{name}.py")

    create_template("task_template.py", path, name, services, auth)

    log.info("Task created: {}", path)


def create_component(project_scaffold, name, services, auth):
    path = project_scaffold.p_path("frontend", "app", "components", name)
    os.makedirs(path, exist_ok=True)

    cpath = os.path.join(path, f"{name}.ts")
    create_template("component_template.ts", cpath, name, services, auth)

    hpath = os.path.join(path, f"{name}.html")
    create_template("component_template.html", hpath, name, services, auth)

    log.info("Component created: {}", path)

    module_path = project_scaffold.p_path("frontend", "app", "custom.module.ts")

    module = None
    with open(module_path) as f:
        module = f.read().splitlines()

    CNAME = "{}Component".format(name.title().replace(" ", ""))

    # Add component import
    import_line = "import {{ {} }} from '@app/components/{}/{}';".format(
        CNAME, name, name
    )
    for idx, row in enumerate(module):
        if import_line in row:
            log.info("Import already included in module file")
            break

        if row.strip().startswith("const") or row.strip().startswith("@"):
            module = module[:idx] + [import_line, ""] + module[idx:]
            log.info("Added {} to module file", import_line)
            break

    # Add component declaration
    for idx, row in enumerate(module):
        if row.strip().startswith("declarations"):
            module = module[: idx + 1] + [f"    {CNAME},"] + module[idx + 1 :]
            log.info("Added {} to module declarations", CNAME)
            break

    templating.make_backup(module_path)
    # Save new module file
    with open(module_path, "w") as f:
        for row in module:
            f.write(f"{row}\n")
        f.write("\n")


def create_service(project_scaffold, name, services, auth):
    path = project_scaffold.p_path("frontend", "app", "services")
    os.makedirs(path, exist_ok=True)

    path = os.path.join(path, f"{name}.ts")

    create_template("service_template.ts", path, name, services, auth)

    log.info("Service created: {}", path)

    module_path = project_scaffold.p_path("frontend", "app", "custom.module.ts")

    module = None
    with open(module_path) as f:
        module = f.read().splitlines()

    SNAME = "{}Service".format(name.title().replace(" ", ""))

    # Add service import
    import_line = f"import {{ {SNAME} }} from '@app/services/{name}';"
    for idx, row in enumerate(module):
        if import_line in row:
            log.info("Import already included in module file")
            break

        if row.strip().startswith("const") or row.strip().startswith("@"):
            module = module[:idx] + [import_line, ""] + module[idx:]
            log.info("Added {} to module file", import_line)
            break

    # Add service declaration
    for idx, row in enumerate(module):
        if row.strip().startswith("declarations"):
            module = module[: idx + 1] + [f"    {SNAME},"] + module[idx + 1 :]
            log.info("Added {} to module declarations", SNAME)
            break

    templating.make_backup(module_path)
    # Save new module file
    with open(module_path, "w") as f:
        for row in module:
            f.write(f"{row}\n")
        f.write("\n")
