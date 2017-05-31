# -*- coding: utf-8 -*-

import os
import re
from urllib.parse import urlparse


def script_abspath(file):
    return os.path.dirname(os.path.realpath(file))


def module_from_package(package):
    return package.split('.')[::-1][0]


def current_dir(*suffixes):
    return os.path.join(os.curdir, *suffixes)


def get_api_url(request_object, production=False):
    """ Get api URL and PORT

    Usefull to handle https and similar
    unfiltering what is changed from nginx and container network configuration

    Warning: it works only if called inside a Flask endpoint
    """

    api_url = request_object.url_root

    if production:
        parsed = urlparse(api_url)
        if parsed.port is not None and parsed.port == 443:
            removed_port = re.sub(r':[\d]+$', '', parsed.netloc)
            api_url = parsed._replace(
                scheme="https", netloc=removed_port
            ).geturl()

    return api_url
