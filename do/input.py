# -*- coding: utf-8 -*-

""" Reading yaml files for this project """

from do import containers_yaml_path
from do.utils.myyaml import load_yaml_file
from do.utils.logs import get_logger

log = get_logger(__name__)

BACKEND_PATH = 'backend'
FRONTEND_PATH = 'frontend'
COMPOSE_FILE = 'docker-compose'
SHORT_YAML_EXT = 'yml'

COMPOSER_DEFAULT_YAMLS = {
    "backend": {
        'file': COMPOSE_FILE,
        'extension': SHORT_YAML_EXT,
        'path': BACKEND_PATH,
        'mandatory': True
    },
    "frontend": {
        'file': COMPOSE_FILE,
        'extension': SHORT_YAML_EXT,
        'path': FRONTEND_PATH,
        'mandatory': False
    }
}


def read_yamls(blueprint, path=containers_yaml_path):

    COMPOSER_VANILLA_YAMLS = {
        "common": {
            'file': 'commons',
            'extension': SHORT_YAML_EXT,
            'path': path,
            'mandatory': False
        },
        "blueprint": {
            'file': blueprint,
            'extension': SHORT_YAML_EXT,
            'path': path,
            'mandatory': True
        }
    }

    files = []
    composers = {**COMPOSER_DEFAULT_YAMLS, **COMPOSER_VANILLA_YAMLS}

    # YAML CHECK UP
    for name, composer in composers.items():

        file = composer.get('file', 'unknown')
        mandatory = composer.pop('mandatory', False)

        try:
            compose = load_yaml_file(**composer)

            if len(compose.get('services', {})) < 1 and mandatory:
                raise AttributeError("Missing services in file %s" % file)
            else:
                files.append(load_yaml_file(return_path=True, **composer))

            # services_data = compose.get('services', {})
            # services_list = list(services_data.keys())
            # log.debug("Services:\n%s" % services_list)

        except KeyError as e:

            if mandatory:
                log.critical_exit(
                    "Composer %s[%s] is mandatory.\n%s" % (name, file, e))
            else:
                log.debug("Missing %s" % name)

    from do.compose import docker_compose
    return docker_compose(files=files)
