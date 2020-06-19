# BEWARE: to not import this package at startup,
# but only into functions otherwise pip will go crazy
# (we cannot understand why, but it does!)

# which version of python is this?
# Retrocompatibility for Python < 3.6
from sultan.api import Sultan

from controller import TESTING, log
from controller.app import Application

try:
    import_exc = (ModuleNotFoundError, ImportError)
except NameError:
    import_exc = ImportError


def install(package, editable=False, user=False, use_pip3=True):

    if use_pip3 and Application.get_bin_version("pip3") is None:  # pragma: no cover
        return install(package=package, editable=editable, user=user, use_pip3=False,)

    try:
        sudo = not user
        # sudo does not work on travis
        if TESTING:
            sudo = False
        with Sultan.load(sudo=sudo) as sultan:
            command = "install --upgrade"
            if editable:
                command += " --editable"
            # --user does not work on travis:
            # Can not perform a '--user' install.
            # User site-packages are not visible in this virtualenv.
            if not TESTING and user:  # pragma: no cover
                command += " --user"
            command += " {}".format(package)

            pip = sultan.pip3 if use_pip3 else sultan.pip
            result = pip(command).run()

            for r in result.stdout:
                print(r)

            for r in result.stderr:
                print(r)
            return result.rc == 0
    except BaseException as e:  # pragma: no cover
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
    except import_exc:  # pylint:disable=catching-non-exception  # pragma: no cover
        return None
    else:
        return package


def package_version(package_name):
    package = import_package(package_name)
    if package is None:  # pragma: no cover
        return None
    return package.__version__
