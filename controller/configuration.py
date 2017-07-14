# -*- coding: utf-8 -*-

""" Reading yaml files for this project """

from controller.compose import Compose
from utilities.myyaml import load_yaml_file, SHORT_YAML_EXT
from utilities.logs import get_logger

log = get_logger(__name__)


def read_yamls(composers):

    base_files = []
    all_files = []

    # YAML CHECK UP
    for name, composer in composers.items():

        if not composer.pop('if', False):
            continue
        else:
            log.very_verbose("Composer %s" % name)

        mandatory = composer.pop('mandatory', False)
        base = composer.pop('base', False)
        composer['extension'] = SHORT_YAML_EXT

        try:
            compose = load_yaml_file(**composer)

            if len(compose.get('services', {})) < 1:
                if mandatory:
                    log.critical_exit("No service defined in file %s" % name)
                else:
                    log.verbose("Skipping")
            else:
                filepath = load_yaml_file(return_path=True, **composer)
                all_files.append(filepath)

                # if path != composer.get('path'):
                if base:
                    base_files.append(filepath)

        except KeyError as e:

            if mandatory:
                log.critical_exit(
                    "Composer %s(%s) is mandatory.\n%s" % (name, filepath, e))
            else:
                log.debug("Missing '%s' composer" % name)

    # to build the config with files and variables
    dc = Compose(files=base_files)
    base_services = dc.config()

    dc = Compose(files=all_files)
    vanilla_services = dc.config()

    return vanilla_services, all_files, base_services, base_files
