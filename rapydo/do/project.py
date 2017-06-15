# -*- coding: utf-8 -*-

from rapydo.utils import configuration
from rapydo.utils.logs import get_logger

log = get_logger(__name__)


def read_configuration(project, is_template=False):
    return configuration.read(project, is_template)


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

        if service.get('environment', {}).get('ACTIVATE', False):
            base_actives.append(name)

    active_services = walk_services(base_actives, dependencies)
    return all_services, active_services


def apply_variables(dictionary={}, variables={}):

    new_dict = {}
    for key, value in dictionary.items():
        if isinstance(value, str) and value.startswith('$$'):
            value = variables.get(value.lstrip('$'), None)
        else:
            pass
        new_dict[key] = value

    return new_dict
