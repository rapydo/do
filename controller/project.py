# -*- coding: utf-8 -*-

from glom import glom

from controller import log


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
        is_active = str(ACTIVATE) == "1"
        if is_active:
            base_actives.append(name)

    log.verbose("Base active services = {}", base_actives)
    log.verbose("Services dependencies = {}", dependencies)
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
