import os
from enum import Enum
from typing import Dict

import typer

from controller import COMPOSE_ENVIRONMENT_FILE, log
from controller.app import Application
from controller.utilities import git


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

        print("{:<12} {:<24} Path".format("Name", "Image"))
        for name, service in Application.data.compose_config.items():
            if name in Application.data.active_services:
                image = service.image
                build = service.build

                if build:
                    build_path = build.context.relative_to(os.getcwd())
                    print(f"{name:<12} {image:<24} {build_path}")
                else:
                    print(f"{name:<12} {image:<24}")

    if element_type == ElementTypes.submodules:
        log.info("List of submodules:\n")
        print("{:<18} {:<18} {}".format("Repo", "Branch", "Path"))
        for name in Application.gits:
            repo = Application.gits.get(name)
            if repo:
                branch = git.get_active_branch(repo)
                path = repo.working_dir
                path = path.replace(os.getcwd(), "")
                if path.startswith("/"):
                    path = path[1:]
                print(f"{name:<18} {branch:<18} {path}")


def read_env() -> Dict[str, str]:
    env: Dict[str, str] = {}
    with open(COMPOSE_ENVIRONMENT_FILE) as f:
        for line in f.readlines():
            tokens = line.split("=")
            k = tokens[0].strip()
            v = tokens[1].strip()
            env[k] = v
    return env
