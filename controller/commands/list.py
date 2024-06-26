"""
Print RAPyDo configurations
"""

import os
from enum import Enum

import typer

from controller import COMPOSE_ENVIRONMENT_FILE, log
from controller.app import Application, Configuration
from controller.deploy.docker import Docker
from controller.utilities import git
from controller.utilities.tables import print_table


class ElementTypes(str, Enum):
    env = "env"
    services = "services"
    submodules = "submodules"


@Application.app.command("list", help="Print rapydo configurations")
def list_cmd(
    element_type: ElementTypes = typer.Argument(
        ..., help="Type of element to be listed"
    ),
) -> None:
    Application.print_command(Application.serialize_parameter("", element_type))
    Application.get_controller().controller_init()

    table: list[list[str]] = []
    if element_type == ElementTypes.env:
        table_title = "List of env variables"
        headers = ["Key", "Value"]
        env = read_env()
        for var in sorted(env):
            val = env.get(var) or ""
            table.append([var, val])

    if element_type == ElementTypes.services:
        table_title = "List of active services"

        headers = ["Name", "Image", "Status", "Path"]

        docker = Docker()
        services_status = docker.get_services_status(Configuration.project)
        for name, service in Application.data.compose_config.items():
            if name in Application.data.active_services:
                image = service.image
                if image is None:  # pragma: no cover
                    image = "N/A"
                build = service.build

                status = services_status.get(name, "N/A")

                if build and build.context:
                    build_path = str(build.context.relative_to(os.getcwd()))
                else:
                    build_path = ""

                table.append([name, image, status, build_path])

    if element_type == ElementTypes.submodules:
        table_title = "List of submodules"
        headers = ["Repo", "Branch", "Path"]
        for name in Application.gits:
            repo = Application.gits.get(name)
            if repo and repo.working_dir:
                branch = git.get_active_branch(repo) or "N/A"
                path = str(repo.working_dir).replace(os.getcwd(), "")
                # to be replacecd with removeprefix
                if path.startswith("/"):
                    path = path[1:]

                table.append([name, branch, path])

    log.info("{}:\n", table_title)
    print_table(headers, table, table_title=table_title)


def read_env() -> dict[str, str]:
    env: dict[str, str] = {}
    with open(COMPOSE_ENVIRONMENT_FILE) as f:
        for line in f.readlines():
            tokens = line.split("=")
            k = tokens[0].strip()
            v = tokens[1].strip()
            env[k] = v
    return env
