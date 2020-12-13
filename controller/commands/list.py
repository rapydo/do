import os
from enum import Enum

import typer

from controller import COMPOSE_ENVIRONMENT_FILE, gitter, log
from controller.app import Application, Configuration
from controller.compose import Compose


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
    Application.get_controller().controller_init()

    if element_type == ElementTypes.env:
        log.info("List env variables:\n")
        env = read_env()
        for var in sorted(env):
            val = env.get(var)
            print(f"{var:<36}\t{val}")

    if element_type == ElementTypes.services:
        log.info("List of active services:\n")

        dc = Compose(files=Application.data.files)
        containers_status = dc.get_containers_status(Configuration.project)

        print("{:<12} {:<8} {:<24} Path".format("Name", "Status", "Image"))
        for service in Application.data.compose_config:
            name = service.get("name")
            if name in Application.data.active_services:
                image = service.get("image")
                build = service.get("build")
                status = containers_status.get(name, "-")

                if build is None:
                    print(f"{name:<12} {status:<8} {image:<24}")
                else:
                    path = build.get("context")
                    path = path.replace(os.getcwd(), "")
                    if path.startswith("/"):
                        path = path[1:]
                    print(f"{name:<12} {status:<8} {image:<24} {path}")

    if element_type == ElementTypes.submodules:
        log.info("List of submodules:\n")
        print("{:<18} {:<18} {}".format("Repo", "Branch", "Path"))
        for name in Application.gits:
            repo = Application.gits.get(name)
            if repo:
                branch = gitter.get_active_branch(repo)
                path = repo.working_dir
                path = path.replace(os.getcwd(), "")
                if path.startswith("/"):
                    path = path[1:]
                print(f"{name:<18} {branch:<18} {path}")


def read_env():
    env = {}
    with open(COMPOSE_ENVIRONMENT_FILE) as f:
        for line in f.readlines():
            tokens = line.split("=")
            k = tokens[0].strip()
            v = tokens[1].strip()
            env[k] = v
    return env
