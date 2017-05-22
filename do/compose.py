# -*- coding: utf-8 -*-

from compose.cli.command import get_config_from_options
from do.utils.logs import get_logger

log = get_logger(__name__)


def docker_compose(files=[]):

    options = {'--file': files}
    _, services_list, _, _, _ = get_config_from_options('.', options)
    # log.pp(services_list)

    # from compose.config.serialize import serialize_config
    # tmp = serialize_config(compose_config)
    # print(tmp)

    return services_list

    # from compose.cli.main import TopLevelCommand
    # t = TopLevelCommand('.')
    # t.config()
