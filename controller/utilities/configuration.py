import sys
from collections import OrderedDict  # can be removed from python 3.7
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml

from controller import log

PROJECTS_DEFAULTS_FILE = Path("projects_defaults.yaml")
PROJECTS_PROD_DEFAULTS_FILE = Path("projects_prod_defaults.yaml")
PROJECT_CONF_FILENAME = Path("project_configuration.yaml")

Configuration = Dict[str, Any]


def read_configuration(
    default_file_path: Path,
    base_project_path: Path,
    projects_path: Path,
    submodules_path: Path,
    read_extended: bool = True,
    production: bool = False,
) -> Tuple[Configuration, Optional[Path], Optional[Path]]:
    """
    Read default configuration
    """

    custom_configuration = load_yaml_file(
        file=PROJECT_CONF_FILENAME, path=base_project_path, keep_order=True
    )

    # Verify custom project configuration
    project = custom_configuration.get("project")
    # Can't be tested because it is included in default configuration
    if project is None:  # pragma: no cover
        raise AttributeError("Missing project configuration")

    variables = ["title", "description", "version", "rapydo"]

    for key in variables:
        # Can't be tested because it is included in default configuration
        if project.get(key) is None:  # pragma: no cover

            log.critical(
                "Project not configured, missing key '{}' in file {}/{}",
                key,
                base_project_path,
                PROJECT_CONF_FILENAME,
            )
            sys.exit(1)

    base_configuration = load_yaml_file(
        file=PROJECTS_DEFAULTS_FILE, path=default_file_path, keep_order=True
    )

    if production:
        base_prod_conf = load_yaml_file(
            file=PROJECTS_PROD_DEFAULTS_FILE,
            path=default_file_path,
            keep_order=True,
        )
        base_configuration = mix_configuration(base_configuration, base_prod_conf)

    if read_extended:
        extended_project = project.get("extends")
    else:
        extended_project = None
    if extended_project is None:
        # Mix default and custom configuration
        return mix_configuration(base_configuration, custom_configuration), None, None

    extends_from = project.get("extends-from", "projects")

    if extends_from == "projects":
        extend_path = projects_path.joinpath(extended_project)
    elif extends_from.startswith("submodules/"):  # pragma: no cover
        repository_name = (extends_from.split("/")[1]).strip()
        if repository_name == "":
            log.critical("Invalid repository name in extends-from, name is empty")
            sys.exit(1)

        extend_path = submodules_path.joinpath(
            repository_name, projects_path, extended_project
        )
    else:  # pragma: no cover
        suggest = "Expected values: 'projects' or 'submodules/${REPOSITORY_NAME}'"
        log.critical("Invalid extends-from parameter: {}.\n{}", extends_from, suggest)
        sys.exit(1)

    if not extend_path.exists():  # pragma: no cover
        log.critical("From project not found: {}", extend_path)
        sys.exit(1)

    extended_configuration = load_yaml_file(
        file=PROJECT_CONF_FILENAME, path=extend_path, keep_order=True
    )

    m1 = mix_configuration(base_configuration, extended_configuration)
    return (
        mix_configuration(m1, custom_configuration),
        extended_project,
        Path(extend_path),
    )


def mix_configuration(
    base: Optional[Configuration], custom: Optional[Configuration]
) -> Configuration:
    if base is None:
        base = {}

    if custom is None:
        return base

    for key, elements in custom.items():

        if key not in base:
            base[key] = custom[key]
            continue

        if elements is None:
            if isinstance(base[key], dict):  # pragma: no cover
                log.warning("Cannot replace {} with empty list", key)
                continue

        if isinstance(elements, dict):
            mix_configuration(base[key], custom[key])

        elif isinstance(elements, list):
            for e in elements:  # pragma: no cover
                base[key].append(e)
        else:
            base[key] = elements

    return base


# ################################
# ######## FROM myyaml.py ########
# ################################


class OrderedLoader(yaml.SafeLoader):
    """
    A workaround good enough to load ordered dictionaries
    https://stackoverflow.com/a/21912744
    """

    pass


def construct_mapping(loader, node):
    loader.flatten_mapping(node)
    return OrderedDict(loader.construct_pairs(node))


def get_yaml_path(file: Path, path: Path) -> Optional[Path]:

    filepath = path.joinpath(file)

    if not filepath.exists():
        return None
    return filepath


def load_yaml_file(
    file: Path, path: Path, keep_order: bool = False, is_optional: bool = False
) -> Configuration:
    """
    Import any data from a YAML file.
    """

    filepath = get_yaml_path(file, path=path)

    if filepath is None:
        if not is_optional:
            log.critical("Failed to read {}/{}: File does not exist", path, file)
            sys.exit(1)
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
                log.critical("YAML file is empty: {}", filepath)
                sys.exit(1)

            # Return value of yaml.load_all is un-annotated and considered as Any
            # But we known that it is a Dict Configuration-compliant
            return docs[0]  # type: ignore

        except Exception as e:
            # # IF dealing with a strange exception string (escaped)
            # import codecs
            # error, _ = codecs.getdecoder("unicode_escape")(str(error))

            log.critical("Failed to read [{}]: {}", filepath, e)
            sys.exit(1)


def read_composer_yamls(
    composers: "OrderedDict[str, Dict[str, Any]]",
) -> Tuple[List[Path], List[Path]]:

    base_files: List[Path] = []
    all_files: List[Path] = []

    # YAML CHECK UP
    for composer in composers.values():

        if not composer.pop("if", False):
            continue

        mandatory = composer.pop("mandatory", False)
        base = composer.pop("base", False)

        try:
            f = Path(str(composer.get("file")))
            p = Path(str(composer.get("path")))
            compose = load_yaml_file(file=f, path=p, is_optional=not mandatory)

            if compose.get("services") is None or len(compose.get("services", {})) < 1:
                continue

            filepath = get_yaml_path(file=f, path=p)

            if filepath:
                all_files.append(filepath)

                if base:
                    base_files.append(filepath)

        except KeyError as e:  # pragma: no cover

            log.critical("Error reading {}: {}", filepath, e)
            sys.exit(1)

    return all_files, base_files
