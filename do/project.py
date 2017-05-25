# -*- coding: utf-8 -*-

from do import defaults_path, project_specs_yaml_path, PROJECT_CONF_FILENAME
from do.utils.myyaml import load_yaml_file
from do.utils.logs import get_logger

log = get_logger(__name__)


def project_configuration():

    # TODO: generalize this in rapydo.utils?

    args = {
        'file': PROJECT_CONF_FILENAME,
        'path': project_specs_yaml_path
    }

    try:
        specs = load_yaml_file(**args)
    except Exception as e:
        log.critical_exit(e)

    prj = specs.get('project')
    if prj is None:
        raise AttributeError("Missing project configuration")
    else:
        check1 = prj.get('title') == 'My project'
        check2 = prj.get('description') == 'Title of my project'
        if check1 or check2:
            filepath = load_yaml_file(return_path=True, **args)
            raise ValueError(
                "\n\nIt seems like your project is not yet configured...\n" +
                "Please edit file %s" % filepath
            )

    # Read default configuration
    defaults = load_yaml_file('defaults', path=defaults_path)
    if len(defaults) < 0:
        raise ValueError("Missing defaults for server configuration!")

    raise NotImplementedError("Help @mattia")
    # Mix default and custom configuration
    # We go deep into two levels down of dictionaries
    for key, elements in defaults.items():
        if key not in specs:
            specs[key] = {}
        for label, element in elements.items():
            if label not in specs[key]:
                specs[key][label] = element

    return specs
