# -*- coding: utf-8 -*-

# BEWARE: to not import this package at startup,
# but only into functions otherwise pip will go crazy
# (we cannot understand why, but it does!)

from utilities.checks import import_exceptions

try:
    from pip.utils import get_installed_distributions
except import_exceptions:
    # from pip 10
    from pip._internal.utils.misc import get_installed_distributions
from sultan.api import Sultan
from utilities.logs import get_logger

log = get_logger(__name__)


def install(package, editable=False, user=False, use_pip3=True):
    with Sultan.load(sudo=True) as sultan:
        command = 'install --upgrade'
        if editable:
            command += " --editable"
        if user:
            command += " --user"
        command += ' %s' % package

        if use_pip3:
            result = sultan.pip3(command).run()
        else:
            result = sultan.pip(command).run()

        for r in result.stdout:
            print(r)

        for r in result.stderr:
            print(r)
        return result.rc == 0


def check_version(package_name):
    for pkg in get_installed_distributions(local_only=True, user_only=False):
        # if pkg.get('_key') == package_name:
        if pkg._key == package_name:  # pylint:disable=protected-access
            # return pkg.get('_version')
            try:
                return pkg._version  # pylint:disable=protected-access
            except AttributeError:
                # fix for python 3.4
                return pkg.__dict__

    return None
