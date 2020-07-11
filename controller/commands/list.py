import os
from enum import Enum

import typer

from controller import COMPOSE_ENVIRONMENT_FILE, gitter, log
from controller.app import Application


class ElementTypes(str, Enum):
    env = "env"
    services = "services"
    submodules = "submodules"


@Application.app.command("list", help="Print rapydo configurations")
def list_cmd(
    element_type: ElementTypes = typer.Argument(
        ..., help="Type of element to be listed"
    ),
):
    Application.controller.controller_init()

    if element_type == ElementTypes.env:
        log.info("List env variables:\n")
        env = read_env()
        for var in sorted(env):
            val = env.get(var)
            print(f"{var:<36}\t{val}")

    if element_type == ElementTypes.services:
        log.info("List of active services:\n")
        print("{:<12} {:<24} {}".format("Name", "Image", "Path"))

        for service in Application.data.compose_config:
            name = service.get("name")
            if name in Application.data.active_services:
                image = service.get("image")
                build = service.get("build")
                if build is None:
                    print(f"{name:<12} {image:<24}")
                else:
                    path = build.get("context")
                    path = path.replace(os.getcwd(), "")
                    if path.startswith("/"):
                        path = path[1:]
                    print(f"{name:<12} {image:<24} {path}")

    if element_type == ElementTypes.submodules:
        log.info("List of submodules:\n")
        print("{:<18} {:<18} {}".format("Repo", "Branch", "Path"))
        for name in Application.gits:
            repo = Application.gits.get(name)
            if repo is None:
                continue
            branch = gitter.get_active_branch(repo)
            path = repo.working_dir
            path = path.replace(os.getcwd(), "")
            if path.startswith("/"):
                path = path[1:]
            print(f"{name:<18} {branch:<18} {path}")


def read_env():
    env = {}
    with open(COMPOSE_ENVIRONMENT_FILE) as f:
        lines = f.readlines()
        for line in lines:
            line = line.split("=")
            k = line[0].strip()
            v = line[1].strip()
            env[k] = v
    return env
