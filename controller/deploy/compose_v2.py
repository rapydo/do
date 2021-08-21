from pathlib import Path
from typing import Any, Dict, List, Union, cast

import yaml
from python_on_whales import DockerClient
from python_on_whales.components.compose.models import ComposeConfig

from controller import (
    COMPOSE_ENVIRONMENT_FILE,
    COMPOSE_FILE,
    SWARM_MODE,
    log,
    print_and_exit,
)
from controller.deploy.docker import Docker


class Compose:
    def __init__(self, files: List[Path]) -> None:
        self.files = files
        self.docker = DockerClient(
            compose_files=cast(List[Union[str, Path]], files),
            compose_env_file=COMPOSE_ENVIRONMENT_FILE.resolve(),
        )

    def get_config(self) -> ComposeConfig:
        # return type is Union[ComposeConfig, Dict[str, Any]] based on return_json
        return self.docker.compose.config(return_json=False)  # type: ignore

    def get_config_json(self) -> Dict[str, Any]:
        # return type is Union[ComposeConfig, Dict[str, Any]] based on return_json
        return self.docker.compose.config(return_json=True)  # type: ignore

    def dump_config(self, services: List[str], set_registry: bool = True) -> None:

        compose_config = self.get_config_json()

        clean_config: Dict[str, Any] = {
            "version": compose_config.get("version", "3.8"),
            "networks": {},
            "volumes": {},
            "services": {},
        }
        networks = set()
        volumes = set()
        binds = set()

        registry = Docker.get_registry()
        # Remove unused services, networks and volumes from compose configuration
        for key, value in compose_config.get("services", {}).items():
            if key not in services:
                continue

            if SWARM_MODE and set_registry and key != "registry":
                value["image"] = f"{registry}/{value['image']}"

            if "healthcheck" in value and "test" in value["healthcheck"]:
                # healtcheck commands can contain env variables double-escaped ($$)
                # When dumped to docker-compose.yml the double escape is removed
                # and when started the single escaped variable is not resolved
                # and breaks the command. Let's double all the $ to restore the
                # expected behavior and counteract the consumed $
                value["healthcheck"]["test"] = [
                    t.replace("$", "$$") for t in value["healthcheck"]["test"]
                ]

            for k, v in value.get("environment", {}).items():
                # Empty variables are converted to None...
                # and None variables are not passed to the container
                # This check can be removed when will be no longer covered
                if v is None:
                    value["environment"][k] = ""

            clean_config["services"][key] = value

            for k in value.get("networks", {}).keys():
                networks.add(k)

            for k in value.get("volumes", []):
                source = k.get("source", "")
                volume_type = k.get("type", "")
                if source and volume_type == "volume":
                    volumes.add(source.split(":")[0])
                elif source and volume_type == "bind":
                    binds.add(source.split(":")[0])

        # Missing folders are then automatically created by the docker engine
        # the runs with root privileges and so create folders as root
        # and this can often lead to issues with permissions.

        for b in binds:
            p = Path(b)
            if p.exists():
                continue
            try:
                p.mkdir(parents=True)
                log.warning(
                    "A bind folder was missing and was automatically created: {}", b
                )
            except PermissionError:
                print_and_exit(
                    "A bind folder is missing and can't be automatically created: {}", b
                )

        for net in networks:
            clean_config["networks"][net] = compose_config["networks"].get(net)

        for vol in volumes:
            clean_config["volumes"][vol] = compose_config["volumes"].get(vol)

        with open(COMPOSE_FILE, "w") as fh:
            fh.write(yaml.dump(clean_config, default_flow_style=False))

        log.debug("Compose configuration dumped on {}", COMPOSE_FILE)
