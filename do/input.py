# -*- coding: utf-8 -*-

""" Reading yaml files for this project """

from do.utils.myyaml import load_yaml_file
from do.utils.logs import get_logger

log = get_logger(__name__)


def read_yamls(blueprint, path):

    try:
        compose = load_yaml_file(
            file=blueprint,
            extension='yml',
            path=path
        )
    except KeyError as e:
        log.critical_exit(e)

    services_data = compose.get('services', {})
    services_list = list(services_data.keys())
    log.debug("Services:\n%s" % services_list)

    return services_data
