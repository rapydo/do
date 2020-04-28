# -*- coding: utf-8 -*-
import os
import yaml
from controller.utilities import system
from controller import log


def __call__(files, active_services, **kwargs):

    #################
    # 1. base dump
    # NOTE: can't figure it out why, but 'dc' on config can't use files
    # so I've used plumbum
    params = []
    for file in files:
        params.append('-f')
        params.append(file)
    params.append('config')
    yaml_string = system.execute_command('docker-compose', parameters=params)

    #################
    # 2. filter active services

    # replacing absolute paths with relative ones
    main_dir = os.getcwd()

    obj = yaml.safe_load(yaml_string.replace(main_dir, '.'))

    active_services = {}
    for key, value in obj.get('services', {}).items():
        if key in active_services:
            active_services[key] = value
    obj['services'] = active_services

    #################
    # 3. write file
    filename = 'docker-compose.yml'
    with open(filename, 'w') as fh:
        fh.write(yaml.dump(obj, default_flow_style=False))
    log.info("Config dump: {}", filename)
