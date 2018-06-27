# -*- coding: utf-8 -*-

from utilities import configuration
from utilities.logs import get_logger
from glom import glom

log = get_logger(__name__)


def walk_services(actives, dependecies, index=0):

    if index >= len(actives):
        return actives

    next_active = actives[index]

    for service in dependecies.get(next_active, []):
        if service not in actives:
            actives.append(service)

    index += 1
    if index >= len(actives):
        return actives
    else:
        return walk_services(actives, dependecies, index)


def find_active(services):
    """
    Check only services involved in current mode,
    which is equal to services 'activated' + 'depends_on'.
    """

    dependencies = {}
    all_services = {}
    base_actives = []

    for service in services:

        name = service.get('name')
        all_services[name] = service
        dependencies[name] = list(service.get('depends_on', {}).keys())

        ACTIVATE = glom(service, "environment.ACTIVATE", default=0)
        is_active = (str(ACTIVATE) == "1")
        if is_active:
            base_actives.append(name)

    active_services = walk_services(base_actives, dependencies)
    return all_services, active_services


def apply_variables(dictionary, variables):

    new_dict = {}
    for key, value in dictionary.items():
        if isinstance(value, str) and value.startswith('$$'):
            value = variables.get(value.lstrip('$'), None)
        else:
            pass
        new_dict[key] = value

    return new_dict


def check_coveralls(path, key='repo_token'):
    compose = configuration.load_yaml_file(path)
    if len(compose.get(key, '').strip()) > 0:
        log.very_verbose('Found the %s' % key)
    else:
        log.exit('Missing "%s": %s' % (key, path))


def check_coverage_service(path, service='coverage'):
    compose = configuration.load_yaml_file(path)
    services = compose.get('services', {})
    if services.get(service) is None:
        log.exit('Missing "%s" service in compose: %s' % (service, path))
    else:
        log.very_verbose('Found %s service' % service)

    return service
