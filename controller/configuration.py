# -*- coding: utf-8 -*-

""" Reading yaml files for this project """

from controller.compose import Compose
from controller.utilities.configuration import load_yaml_file
from controller import log


def read_yamls(composers):

    base_files = []
    all_files = []

    # YAML CHECK UP
    for name, composer in composers.items():

        if not composer.pop('if', False):
            continue

        log.verbose("Composer {}", name)

        mandatory = composer.pop('mandatory', False)
        base = composer.pop('base', False)
        composer['extension'] = 'yml'

        try:
            compose = load_yaml_file(**composer)

            if len(compose.get('services', {})) < 1:
                if mandatory:
                    log.exit("No service defined in file {}", name)
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
                log.exit(
                    "Composer %s(%s) is mandatory.\n%s" % (name, filepath, e)
                )
            else:
                log.debug("Missing '{}' composer", name)

    # to build the config with files and variables
    dc = Compose(files=base_files)
    base_services = dc.config()

    dc = Compose(files=all_files)
    vanilla_services = dc.config()

    return vanilla_services, all_files, base_services, base_files
