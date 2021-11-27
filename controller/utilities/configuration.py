from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, cast

import yaml

from controller import COMPOSE_FILE_VERSION, CONFS_DIR, log, print_and_exit

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
        file=base_project_path.joinpath(PROJECT_CONF_FILENAME)
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

            print_and_exit(
                "Project not configured, missing key '{}' in file {}/{}",
                key,
                base_project_path,
                PROJECT_CONF_FILENAME,
            )

    base_configuration = load_yaml_file(
        file=default_file_path.joinpath(PROJECTS_DEFAULTS_FILE)
    )

    if production:
        base_prod_conf = load_yaml_file(
            file=default_file_path.joinpath(PROJECTS_PROD_DEFAULTS_FILE)
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
            print_and_exit("Invalid repository name in extends-from, name is empty")

        extend_path = submodules_path.joinpath(
            repository_name, projects_path, extended_project
        )
    else:  # pragma: no cover
        suggest = "Expected values: 'projects' or 'submodules/${REPOSITORY_NAME}'"
        print_and_exit("Invalid extends-from parameter: {}.\n{}", extends_from, suggest)

    if not extend_path.exists():  # pragma: no cover
        print_and_exit("From project not found: {}", extend_path)

    extended_configuration = load_yaml_file(
        file=extend_path.joinpath(PROJECT_CONF_FILENAME)
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


def load_yaml_file(
    file: Path, keep_order: bool = False, is_optional: bool = False
) -> Configuration:
    """
    Import any data from a YAML file.
    """

    if not file.exists():
        if not is_optional:
            print_and_exit("Failed to read {}: File does not exist", file)
        return {}

    with open(file) as fh:
        try:
            docs = list(yaml.safe_load_all(fh))

            if not docs:
                print_and_exit("YAML file is empty: {}", file)

            # Return value of yaml.safe_load_all is un-annotated and considered as Any
            # But we known that it is a Dict Configuration-compliant
            return cast(Configuration, docs[0])

        except Exception as e:
            # # IF dealing with a strange exception string (escaped)
            # import codecs
            # error, _ = codecs.getdecoder("unicode_escape")(str(error))

            print_and_exit("Failed to read [{}]: {}", file, str(e))


def read_composer_yamls(config_files: List[Path]) -> Tuple[List[Path], List[Path]]:

    base_files: List[Path] = []
    all_files: List[Path] = []

    # YAML CHECK UP
    for path in config_files:

        try:

            # This is to verify that mandatory files exist and yml syntax is valid
            conf = load_yaml_file(file=path, is_optional=False)

            if conf.get("version") != COMPOSE_FILE_VERSION:  # pragma: no cover
                log.warning(
                    "Compose file version in {} is {}, expected {}",
                    path,
                    conf.get("version"),
                    COMPOSE_FILE_VERSION,
                )

            if path.exists():
                all_files.append(path)

                # Base files are those loaded from CONFS_DIR
                if CONFS_DIR in path.parents:
                    base_files.append(path)

        except KeyError as e:  # pragma: no cover

            print_and_exit("Error reading {}: {}", path, str(e))

    return all_files, base_files
