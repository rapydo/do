import os
from pathlib import Path
from typing import Any, Dict

import yaml

from controller import log
from controller.app import Application
from controller.compose import Compose


@Application.app.command(help="Dump current config into docker compose YAML")
def dump() -> None:
    Application.get_controller().controller_init()

    #################
    # 1. base dump
    dc = Compose(Application.data.files)
    yaml_string = dc.dump_config()

    #################
    # 2. filter active services

    # replacing absolute paths with relative ones
    complete_config = yaml.safe_load(yaml_string.replace(os.getcwd(), "."))

    clean_config: Dict[str, Any] = {
        "version": complete_config.get("version", "3.8"),
        "networks": {},
        "volumes": {},
        "services": {},
    }
    networks = set()
    volumes = set()
    # Remove unused services, networks and volumes from compose configuration
    for key, value in complete_config.get("services", {}).items():
        if key not in Application.data.active_services:
            continue
        clean_config["services"][key] = value

        for k in value.get("networks", {}).keys():
            networks.add(k)

        for k in value.get("volumes", []):
            if k.startswith("./"):
                continue
            volumes.add(k.split(":")[0])

    for net in networks:
        clean_config["networks"][net] = complete_config["networks"].get(net)

    for vol in volumes:
        clean_config["volumes"][vol] = complete_config["volumes"].get(vol)
    #################
    # 3. write file
    filename = Path("docker-compose.yml")
    with open(filename, "w") as fh:
        fh.write(yaml.dump(clean_config, default_flow_style=False))
    log.info("Config dump: {}", filename)
