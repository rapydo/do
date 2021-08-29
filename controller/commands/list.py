import os
from enum import Enum
from typing import Dict, Union

import typer

from controller import COMPOSE_ENVIRONMENT_FILE, SWARM_MODE, log
from controller.app import Application, Configuration
from controller.deploy.compose_v2 import Compose
from controller.deploy.swarm import Swarm
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

        header = ("Name", "Image", "Status", "Path")

        if SWARM_MODE:
            engine: Union[Swarm, Compose] = Swarm()
        else:
            engine = Compose(Application.data.files)

        services_status = engine.get_services_status(Configuration.project)
        print(f"{header[0]:<12} {header[1]:<24} {header[2]:<12} {header[3]}")
        for name, service in Application.data.compose_config.items():
            if name in Application.data.active_services:
                image = service.image
                build = service.build

                status = services_status.get(name, "N/A")

                if build:
                    build_path = build.context.relative_to(os.getcwd())
                    print(f"{name:<12} {image:<24} {status:12} {build_path}")
                else:
                    print(f"{name:<12} {image:<24} {status:12}")

    if element_type == ElementTypes.submodules:
        log.info("List of submodules:\n")
        print("{:<18} {:<18} {}".format("Repo", "Branch", "Path"))
        for name in Application.gits:
            repo = Application.gits.get(name)
            if repo and repo.working_dir:
                branch = git.get_active_branch(repo)
                path = str(repo.working_dir).replace(os.getcwd(), "")
                # to be replacecd with removeprefix
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
