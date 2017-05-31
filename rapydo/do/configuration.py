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

COMPOSER_BACKEND_YAML = {
    'name': 'backend',
    'file': COMPOSE_FILE,
    'extension': SHORT_YAML_EXT,
    'path': BACKEND_PATH,
    'mandatory': True
}
COMPOSER_FRONTEND_YAML = {
    'name': 'frontend',
    'file': COMPOSE_FILE,
    'extension': SHORT_YAML_EXT,
    'path': FRONTEND_PATH,
    'mandatory': False
}


def read_yamls(blueprint, frontend=False, path=None):

    if path is None:
        path = helpers.current_dir(CONTAINERS_YAML_DIRNAME)

    composers = []
    base_files = []
    all_files = []

    composers.append(COMPOSER_BACKEND_YAML)
    if frontend:
        composers.append(COMPOSER_FRONTEND_YAML)

    composers.append({
        'name': 'common', 'file': 'commons',
        'extension': SHORT_YAML_EXT, 'path': path, 'mandatory': False
    })

    composers.append({
        'name': 'blueprint', 'file': blueprint,
        'extension': SHORT_YAML_EXT, 'path': path, 'mandatory': True
    })

    # YAML CHECK UP
    for composer in composers:

        name = composer.pop('name')
        file = composer.get('file', 'unknown')
        mandatory = composer.pop('mandatory', False)

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
                if path != composer.get('path'):
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
