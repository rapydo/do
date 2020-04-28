# -*- coding: utf-8 -*-

# BEWARE: to not import this package at startup,
# but only into functions otherwise pip will go crazy
# (we cannot understand why, but it does!)

# which version of python is this?
# Retrocompatibility for Python < 3.6
from sultan.api import Sultan
try:
    import_exceptions = (ModuleNotFoundError, ImportError)
except NameError:
    import_exceptions = ImportError
from controller import log


def install(package, editable=False, user=False, use_pip3=True):
    try:
        with Sultan.load(sudo=not user) as sultan:
            command = 'install --upgrade'
            if editable:
                command += " --editable"
            if user:
                command += " --user"
            command += ' {}'.format(package)

            if use_pip3:
                result = sultan.pip3(command).run()
            else:
                result = sultan.pip(command).run()

            for r in result.stdout:
                print(r)

            for r in result.stderr:
                print(r)
            return result.rc == 0
    except BaseException as e:
        log.exit(e)


def check_version(package_name):

    # Don't import before or pip will mess up everything! Really crazy
    from pip._internal.utils.misc import get_installed_distributions
    for pkg in get_installed_distributions(local_only=True, user_only=False):
        if pkg._key == package_name:  # pylint:disable=protected-access
            return pkg._version  # pylint:disable=protected-access

    return None


def import_package(package_name):

    from importlib import import_module

    try:
        package = import_module(package_name)
    except import_exceptions:  # pylint:disable=catching-non-exception
        return None
    else:
        return package


def package_version(package_name):
    package = import_package(package_name)
    if package is None:
        return None
    try:
        version = package.__version__
        if isinstance(version, str):
            return version

        # Fix required for requests
        return version.__version__
    except BaseException as e:
        print(str(e))
        return None
