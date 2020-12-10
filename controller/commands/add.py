from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict

import typer
from glom import glom

from controller import log
from controller.app import Application, Configuration
from controller.project import Project
from controller.templating import Templating


class ElementTypes(str, Enum):
    endpoint = "endpoint"
    task = "task"
    component = "component"
    service = "service"
    integration_test = "integration_test"


def get_function(
    element: ElementTypes,
) -> Callable[[Project, str, Any, str, bool, bool], None]:

    if element == "endpoint":
        return create_endpoint

    if element == "task":
        return create_task

    if element == "component":
        return create_component

    if element == "service":
        return create_service

    if element == "integration_test":
        return create_integration_test

    # Can't be reached
    return create_service  # pragma: no cover


@Application.app.command(help="Add a new element")
def add(
    element_type: ElementTypes = typer.Argument(
        ..., help="Type of element to be created"
    ),
    name: str = typer.Argument(..., help="Name to be assigned to the new element"),
    force: bool = typer.Option(
        False,
        "--force",
        help="Force files overwriting",
        show_default=False,
    ),
    add_tests: bool = typer.Option(
        False,
        "--add-tests",
        help="Add tests files",
        show_default=False,
    ),
) -> None:

    Application.get_controller().controller_init()

    auth = glom(Configuration.specs, "variables.env.AUTH_SERVICE", default=None)

    fn = get_function(element_type)

    fn(
        Application.project_scaffold,
        name,
        Application.data.services,
        auth,
        force,
        add_tests,
    )


def create_template(
    templating: Templating,
    template_name: str,
    target_path: Path,
    name: str,
    services: Dict[str, str],
    auth: str,
    force: bool,
) -> None:

    if not force and target_path.exists():
        Application.exit("{} already exists", target_path)

    template = templating.get_template(
        template_name, {"name": name, "services": services, "auth": auth}
    )

    templating.save_template(target_path, template, force=force)


def create_endpoint(
    project_scaffold: Project,
    name: str,
    services: Any,
    auth: str,
    force: bool,
    add_tests: bool,
) -> None:
    path = project_scaffold.p_path("backend", "endpoints")
    path = path.joinpath(f"{name}.py")

    templating = Templating()
    create_template(
        templating, "endpoint_template.py", path, name, services, auth, force
    )

    log.info("Endpoint created: {}", path)

    if add_tests:
        path = project_scaffold.p_path("backend", "tests")
        path = path.joinpath(f"test_endpoints_{name}.py")

        create_template(
            templating, "endpoint_test_template.py", path, name, services, auth, force
        )

        log.info("Tests scaffold created: {}", path)


def create_task(
    project_scaffold: Project,
    name: str,
    services: Any,
    auth: str,
    force: bool,
    add_tests: bool,
) -> None:
    path = project_scaffold.p_path("backend", "tasks")
    path = path.joinpath(f"{name}.py")

    templating = Templating()
    create_template(templating, "task_template.py", path, name, services, auth, force)

    log.info("Task created: {}", path)

    if add_tests:
        log.warning("Tests for tasks not implemented yet")


def create_component(
    project_scaffold: Project,
    name: str,
    services: Any,
    auth: str,
    force: bool,
    add_tests: bool,
) -> None:
    path = project_scaffold.p_path("frontend", "app", "components", name)
    path.mkdir(parents=True, exist_ok=True)

    # Used by Frontend during tests
    is_sink_special_case = name == "sink"

    if is_sink_special_case:
        template_ts = "sink.ts"
        template_html = "sink.html"
    else:
        template_ts = "component_template.ts"
        template_html = "component_template.html"

    cpath = path.joinpath(f"{name}.ts")
    templating = Templating()
    create_template(templating, template_ts, cpath, name, services, auth, force)

    hpath = path.joinpath(f"{name}.html")
    create_template(templating, template_html, hpath, name, services, auth, force)

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

    # Add sink route
    if is_sink_special_case:
        for idx, row in enumerate(module):
            if row.strip().startswith("const routes: Routes = ["):
                ROUTE = """
  {
    path: "app/sink",
    component: SinkComponent,
  },

"""
                module = module[: idx + 1] + [ROUTE] + module[idx + 1 :]
                log.info("Added route to module declarations")
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

    if add_tests:
        path = project_scaffold.p_path("frontend", "app", "components", name)
        path = path.joinpath(f"{name}.spec.ts")

        create_template(
            templating,
            "component_test_template.spec.ts",
            path,
            name,
            services,
            auth,
            force,
        )

        log.info("Tests scaffold created: {}", path)


def create_service(
    project_scaffold: Project,
    name: str,
    services: Any,
    auth: str,
    force: bool,
    add_tests: bool,
) -> None:
    path = project_scaffold.p_path("frontend", "app", "services")
    path.mkdir(parents=True, exist_ok=True)

    path = path.joinpath(f"{name}.ts")

    templating = Templating()
    create_template(
        templating, "service_template.ts", path, name, services, auth, force
    )

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

    if add_tests:
        log.warning("Tests for services not implemented yet")


def create_integration_test(
    project_scaffold: Project,
    name: str,
    services: Any,
    auth: str,
    force: bool,
    add_tests: bool,
) -> None:

    if add_tests:
        Application.exit("Add integration_test does not support --add-tests flag")

    path = project_scaffold.p_path("frontend", "integration")

    # Expected name is a route-like string, e.g. app/mypath/:my_id

    # Let's replace the name with a path safe version
    # -> app_mypath_my_id
    # To be replaced with removeprefix
    # Initial / always removed... than will be added
    if name.startswith("/"):
        name = name[1:]

    filename = name.replace("/", "_").replace(":", "")
    path = path.joinpath(f"{filename}.spec.ts")

    templating = Templating()
    create_template(
        templating, "cypress_template.spec.ts", path, f"/{name}", services, auth, force
    )

    log.info("Integration test created: {}", path)
