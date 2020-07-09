import os

import yaml

from controller import log
from controller.app import Application
from controller.utilities import system


@Application.app.command(help="Dump current config into docker compose YAML")
def dump():

    #################
    # 1. base dump
    # NOTE: can't figure it out why, but 'dc' on config can't use files
    # so I've used plumbum
    params = []
    for file in Application.data.files:
        params.append("-f")
        params.append(file)
    params.append("config")
    yaml_string = system.execute_command("docker-compose", parameters=params)

    #################
    # 2. filter active services

    # replacing absolute paths with relative ones
    main_dir = os.getcwd()

    obj = yaml.safe_load(yaml_string.replace(main_dir, "."))

    services_list = {}
    # Remove not active services from compose configuration
    for key, value in obj.get("services", {}).items():
        if key in Application.data.active_services:
            services_list[key] = value
    obj["services"] = services_list

    #################
    # 3. write file
    filename = "docker-compose.yml"
    with open(filename, "w") as fh:
        fh.write(yaml.dump(obj, default_flow_style=False))
    log.info("Config dump: {}", filename)
