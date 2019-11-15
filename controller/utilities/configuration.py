# -*- coding: utf-8 -*-

import os
import yaml
from collections import OrderedDict
from controller import log

PROJECTS_DEFAULTS_FILE = 'projects_defaults'
PROJECT_CONF_FILENAME = 'project_configuration'


def load_project_configuration(path, file=None, do_exit=True):

    if file is None:
        file = PROJECT_CONF_FILENAME

    args = {
        'path': path,
        'skip_error': False,
        'file': file,
        'keep_order': True,
    }
    try:
        log.verbose("Found '%s/%s' configuration", path, file)
        return load_yaml_file(**args)
    except AttributeError as e:
        if do_exit:
            log.exit(e)
        else:
            raise AttributeError(e)


def read(
    default_file_path,
    base_project_path,
    projects_path,
    submodules_path,
    from_container=False,
    read_extended=True,
    do_exit=True,
):
    """
    Read default configuration
    """

    custom_configuration = load_project_configuration(
        base_project_path, file=PROJECT_CONF_FILENAME, do_exit=do_exit
    )

    # Verify custom project configuration
    project = custom_configuration.get('project')
    if project is None:
        raise AttributeError("Missing project configuration")

    variables = ['title', 'description', 'version', 'rapydo']

    for key in variables:
        if project.get(key) is None:

            log.critical_exit(
                "Project not configured, missing key '%s' in file %s/%s.yaml",
                key,
                base_project_path,
                PROJECT_CONF_FILENAME,
            )

    if default_file_path is None:
        base_configuration = {}
    else:
        base_configuration = load_project_configuration(
            default_file_path, file=PROJECTS_DEFAULTS_FILE, do_exit=do_exit
        )

    if read_extended:
        extended_project = project.get('extends')
    else:
        extended_project = None
    if extended_project is None:
        # Mix default and custom configuration
        return mix(base_configuration, custom_configuration), None, None

    extends_from = project.get('extends-from', 'projects')

    if extends_from == "projects":
        extend_path = projects_path
    elif extends_from.startswith("submodules/"):
        repository_name = (extends_from.split("/")[1]).strip()
        if repository_name == '':
            log.exit('Invalid repository name in extends-from, name is empty')

        if from_container:
            extend_path = submodules_path
        else:
            extend_path = os.path.join(submodules_path, repository_name, projects_path)
    else:
        suggest = "Expected values: 'projects' or 'submodules/${REPOSITORY_NAME}'"
        log.exit("Invalid extends-from parameter: %s.\n%s", extends_from, suggest)

    # in container the file is mounted in the confs folder
    # otherwise will be in projects/projectname or submodules/projectname
    if not from_container:
        extend_path = os.path.join(extend_path, extended_project)

    if not os.path.exists(extend_path):
        log.critical_exit("From project not found: %s", extend_path)

    # on backend is mounted with `extended_` prefix
    if from_container:
        extend_file = "extended_%s" % (PROJECT_CONF_FILENAME)
    else:
        extend_file = PROJECT_CONF_FILENAME
    extended_configuration = load_project_configuration(
        extend_path, file=extend_file, do_exit=do_exit
    )

    m1 = mix(base_configuration, extended_configuration)
    return mix(m1, custom_configuration), extended_project, extend_path


def mix(base, custom):
    if base is None:
        base = {}

    for key, elements in custom.items():

        if key not in base:
            # log.info("Adding %s to configuration" % key)
            base[key] = custom[key]
            continue

        if elements is None:
            if isinstance(base[key], dict):
                log.warning("Cannot replace %s with empty list", key)
                continue

        if isinstance(elements, dict):
            mix(base[key], custom[key])

        elif isinstance(elements, list):
            for e in elements:
                base[key].append(e)
        else:
            # log.info("Replacing default %s in configuration" % key)
            base[key] = elements

    return base

# ################################
# ######## FROM myyaml.py ########
# ################################


def get_yaml_path(path, filename, extension):
    if path is None:
        filepath = filename
    else:
        if extension is not None:
            filename += '.' + extension
        filepath = os.path.join(path, filename)

    return filepath


def regular_load(stream, loader=yaml.loader.Loader):
    # LOAD fails if more than one document is there
    # return yaml.load(fh)

    # LOAD ALL gets more than one document inside the file
    # gen = yaml.load_all(fh)
    return yaml.load_all(stream, loader)


class OrderedLoader(yaml.SafeLoader):
    """
    A 'workaround' good enough for ordered loading of dictionaries

    https://stackoverflow.com/a/21912744

    NOTE: This was created to skip dependencies.
    Otherwise this option could be considered:
    https://pypi.python.org/pypi/ruamel.yaml
    """

    pass


def construct_mapping(loader, node):
    loader.flatten_mapping(node)
    return OrderedDict(loader.construct_pairs(node))


def ordered_load(stream):

    OrderedLoader.add_constructor(
        yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, construct_mapping
    )
    # return yaml.load(stream, OrderedLoader)
    return regular_load(stream, OrderedLoader)


def load_yaml_file(
    file,
    path=None,
    get_all=False,
    skip_error=False,
    extension='yaml',
    return_path=False,
    keep_order=False,
):
    """
    Import any data from a YAML file.
    """

    filepath = get_yaml_path(path, file, extension)

    log.verbose("Reading file %s" % filepath)

    # load from this file
    error = None
    if not os.path.exists(filepath):
        error = 'File does not exist'
    else:
        if return_path:
            return filepath

        with open(filepath) as fh:
            try:
                if keep_order:
                    loader = ordered_load(fh)
                else:
                    loader = regular_load(fh)
            except Exception as e:
                error = e
            else:
                docs = list(loader)
                if get_all:
                    return docs

                if len(docs) > 0:
                    return docs[0]

                message = "YAML file is empty: %s" % filepath
                log.exit(message)

    # # IF dealing with a strange exception string (escaped)
    # import codecs
    # error, _ = codecs.getdecoder("unicode_escape")(str(error))

    message = "Failed to read YAML file [%s]: %s" % (filepath, error)
    log.warning(message)
    return {}
