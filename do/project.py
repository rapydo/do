# -*- coding: utf-8 -*-

from do import defaults_path, project_specs_yaml_path, PROJECT_CONF_FILENAME
from do.utils.myyaml import load_yaml_file
from do.utils.logs import get_logger

log = get_logger(__name__)


def project_configuration():

    # TODO: generalize this in rapydo.utils?

    # Read default configuration
    specs = load_yaml_file('defaults', path=defaults_path)
    if len(specs) < 0:
        raise ValueError("Missing defaults for server configuration!")

    # Read custom project configuration
    args = {
        'file': PROJECT_CONF_FILENAME,
        'path': project_specs_yaml_path
    }
    custom = load_yaml_file(**args)

    # Verify custom project configuration
    prj = custom.get('project')
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
