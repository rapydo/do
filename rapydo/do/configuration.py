# -*- coding: utf-8 -*-

""" Reading yaml files for this project """

from rapydo.do import CONTAINERS_YAML_DIRNAME
from rapydo.do.compose import Compose
from rapydo.utils import helpers
from rapydo.utils.myyaml import load_yaml_file
from rapydo.utils.logs import get_logger

log = get_logger(__name__)

BACKEND_PATH = 'backend'
FRONTEND_PATH = 'frontend'
COMPOSE_FILE = 'docker-compose'
SHORT_YAML_EXT = 'yml'


def read_yamls(blueprint, frontend=False, path=None):

    if path is None:
        path = helpers.current_dir(CONTAINERS_YAML_DIRNAME)

    composers = []
    base_files = []
    all_files = []

    # FIXME: move this dictionaries into defaults

    ######################
    # Base = backend + frontend
    composers.append({
        'name': 'backend', 'file': 'backend', 'base': True,
        'extension': SHORT_YAML_EXT, 'path': path, 'mandatory': True
    })

    if frontend:
        composers.append({
            'name': 'frontend', 'file': 'frontend', 'base': True,
            'extension': SHORT_YAML_EXT, 'path': path, 'mandatory': False
        })

    ######################
    # vanilla = commons + blueprint
    composers.append({
        'name': 'common', 'file': 'commons', 'base': False,
        'extension': SHORT_YAML_EXT, 'path': path, 'mandatory': False
    })

    composers.append({
        'name': 'blueprint', 'file': blueprint, 'base': False,
        'extension': SHORT_YAML_EXT, 'path': path, 'mandatory': True
    })

    # YAML CHECK UP
    for composer in composers:

        name = composer.pop('name')
        file = composer.get('file', 'unknown')
        mandatory = composer.pop('mandatory', False)
        base = composer.pop('base', False)

        try:
            compose = load_yaml_file(**composer)

            if len(compose.get('services', {})) < 1:
                if mandatory:
                    log.critical_exit("No service defined in file %s" % file)
                else:
                    log.verbose("Skipping")
            else:
                filepath = load_yaml_file(return_path=True, **composer)
                all_files.append(filepath)

                # if path != composer.get('path'):
                if base:
                    base_files.append(filepath)

        except KeyError as e:

            if mandatory:
                log.critical_exit(
                    "Composer %s[%s] is mandatory.\n%s" % (name, file, e))
            else:
                log.debug("Missing '%s' composer" % name)

    # to build the config with files and variables
    dc = Compose(files=base_files)
    base_services = dc.config()

    dc = Compose(files=all_files)
    vanilla_services = dc.config()

    return vanilla_services, all_files, base_services, base_files
