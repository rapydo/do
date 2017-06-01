# -*- coding: utf-8 -*-

from rapydo.do import PROJECT_YAML_SPECSDIR, PROJECT_CONF_FILENAME
from rapydo.utils import helpers
from rapydo.utils.myyaml import load_yaml_file
from rapydo.utils.logs import get_logger

log = get_logger(__name__)


def configuration(development=False):

    # TODO: generalize this in rapydo.utils?

    ##################
    # Read default configuration
    args = {
        'path': helpers.current_dir(PROJECT_YAML_SPECSDIR),
        'skip_error': False,
        'logger': False
    }

    confs = {}
    for f in 'defaults', PROJECT_CONF_FILENAME:
        args['file'] = f
        try:
            confs[f] = load_yaml_file(**args)
            log.debug("(CHECKED) found '%s' rapydo configuration" % f)
        except AttributeError as e:
            log.critical_exit(e)

    specs = confs['defaults']
    custom = confs[PROJECT_CONF_FILENAME]

    # Verify custom project configuration
    prj = custom.get('project')
    if prj is None:
        raise AttributeError("Missing project configuration")
    elif not development:
        check1 = prj.get('title') == 'My project'
        check2 = prj.get('description') == 'Title of my project'
        check3 = prj.get('name') == 'rapydo'
        if check1 or check2 or check3:
            filepath = load_yaml_file(return_path=True, **args)
            log.critical_exit(
                "\n\nIt seems like your project is not yet configured...\n" +
                "Please edit file %s" % filepath
            )

    # Mix default and custom configuration
    return mix_dictionary(specs, custom)


def mix_dictionary(base, custom):

    for key, elements in custom.items():

        if key not in base:
            # log.info("Adding %s to configuration" % key)
            base[key] = custom[key]
            continue

        if isinstance(elements, dict):
            mix_dictionary(base[key], custom[key])
        else:
            # log.info("Replacing default %s in configuration" % key)
            base[key] = elements

    return base


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
    Check only services involved in current blueprint,
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
        new_dict[key] = value

    return new_dict
