# -*- coding: utf-8 -*-

import os
from collections import OrderedDict
import yaml
from controller import log

PROJECTS_DEFAULTS_FILE = 'projects_defaults.yaml'
PROJECTS_PROD_DEFAULTS_FILE = 'projects_prod_defaults.yaml'
PROJECT_CONF_FILENAME = 'project_configuration.yaml'


def read_configuration(
    default_file_path,
    base_project_path,
    projects_path,
    submodules_path,
    read_extended=True,
    production=False
):
    """
    Read default configuration
    """

    custom_configuration = load_yaml_file(
        file=PROJECT_CONF_FILENAME, path=base_project_path, keep_order=True
    )

    # Verify custom project configuration
    project = custom_configuration.get('project')
    if project is None:
        raise AttributeError("Missing project configuration")

    variables = ['title', 'description', 'version', 'rapydo']

    for key in variables:
        if project.get(key) is None:

            log.exit(
                "Project not configured, missing key '{}' in file {}/{}",
                key,
                base_project_path,
                PROJECT_CONF_FILENAME,
            )

    if default_file_path is None:
        base_configuration = {}
    else:
        base_configuration = load_yaml_file(
            file=PROJECTS_DEFAULTS_FILE,
            path=default_file_path,
            keep_order=True
        )

        if production:
            base_prod_conf = load_yaml_file(
                file=PROJECTS_PROD_DEFAULTS_FILE,
                path=default_file_path,
                keep_order=True
            )
            base_configuration = mix_configuration(base_configuration, base_prod_conf)

    if read_extended:
        extended_project = project.get('extends')
    else:
        extended_project = None
    if extended_project is None:
        # Mix default and custom configuration
        return mix_configuration(base_configuration, custom_configuration), None, None

    extends_from = project.get('extends-from', 'projects')

    if extends_from == "projects":
        extend_path = projects_path
    elif extends_from.startswith("submodules/"):
        repository_name = (extends_from.split("/")[1]).strip()
        if repository_name == '':
            log.exit('Invalid repository name in extends-from, name is empty')

        extend_path = os.path.join(submodules_path, repository_name, projects_path)
    else:
        suggest = "Expected values: 'projects' or 'submodules/${REPOSITORY_NAME}'"
        log.exit("Invalid extends-from parameter: {}.\n{}", extends_from, suggest)

    extend_path = os.path.join(extend_path, extended_project)

    if not os.path.exists(extend_path):
        log.exit("From project not found: {}", extend_path)

    extended_configuration = load_yaml_file(
        file=PROJECT_CONF_FILENAME, path=extend_path, keep_order=True
    )

    m1 = mix_configuration(base_configuration, extended_configuration)
    return mix_configuration(m1, custom_configuration), extended_project, extend_path


def mix_configuration(base, custom):
    if base is None:
        base = {}

    for key, elements in custom.items():

        if key not in base:
            base[key] = custom[key]
            continue

        if elements is None:
            if isinstance(base[key], dict):
                log.warning("Cannot replace {} with empty list", key)
                continue

        if isinstance(elements, dict):
            mix_configuration(base[key], custom[key])

        elif isinstance(elements, list):
            for e in elements:
                base[key].append(e)
        else:
            base[key] = elements

    return base

# ################################
# ######## FROM myyaml.py ########
# ################################


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


def get_yaml_path(file, path):

    filepath = os.path.join(path, file)

    log.verbose("Reading file {}", filepath)

    if not os.path.exists(filepath):
        return None
    return filepath


def load_yaml_file(file, path, keep_order=False, is_optional=False):
    """
    Import any data from a YAML file.
    """

    filepath = get_yaml_path(file, path=path)

    if filepath is None:
        if is_optional:
            log.info(
                "Failed to read YAML file {}/{}: File does not exist",
                path, file,
            )
        else:
            log.exit(
                "Failed to read YAML file {}/{}: File does not exist",
                path, file,
            )
        return {}

    with open(filepath) as fh:
        try:
            if keep_order:

                OrderedLoader.add_constructor(
                    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, construct_mapping
                )
                loader = yaml.load_all(fh, OrderedLoader)
            else:
                loader = yaml.load_all(fh, yaml.loader.Loader)

            docs = list(loader)

            if len(docs) == 0:
                log.exit("YAML file is empty: {}", filepath)

            return docs[0]

        except Exception as e:
            # # IF dealing with a strange exception string (escaped)
            # import codecs
            # error, _ = codecs.getdecoder("unicode_escape")(str(error))

            log.warning("Failed to read YAML file [{}]: {}", filepath, e)
            return {}


def read_composer_yamls(composers):

    base_files = []
    all_files = []

    # YAML CHECK UP
    for name, composer in composers.items():

        if not composer.pop('if', False):
            continue

        log.verbose("Composer {}", name)

        mandatory = composer.pop('mandatory', False)
        base = composer.pop('base', False)

        try:
            f = composer.get('file')
            p = composer.get('path')
            compose = load_yaml_file(file=f, path=p, is_optional=not mandatory)

            if compose.get('services') is None or len(compose.get('services', {})) < 1:
                # if mandatory:
                #     log.exit("No service defined in file {}", name)
                # else:
                #     log.verbose("No service defined in {}, skipping", name)
                log.verbose("No service defined in {}, skipping", name)
                continue

            filepath = get_yaml_path(file=f, path=p)
            all_files.append(filepath)

            if base:
                base_files.append(filepath)

        except KeyError as e:

            # if mandatory:
            #     log.exit(
            #         "Composer {}({}) is mandatory.\n{}", name, filepath, e
            #     )
            # else:
            #     log.debug("Missing '{}' composer", name)
            log.exit("Error loading {}: {}", filepath, e)

    return all_files, base_files
