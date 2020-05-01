# -*- coding: utf-8 -*-
import os
from controller import SUBMODULES_DIR
from controller import gitter
from controller import log


def install_controller_from_pip(version, user):

    # BEWARE: to not import this package outside the function
    # Otherwise pip will go crazy
    # (we cannot understand why, but it does!)
    from controller.packages import install

    log.info("You asked to install rapydo-controller {} from pip", version)

    package = "rapydo-controller"
    controller = "{}=={}".format(package, version)
    installed = install(controller, user=user)
    if not installed:
        log.error("Unable to install controller {} from pip", version)
    else:
        log.info("Controller version {} installed from pip", version)


def install_controller_from_git(version, user):

    # BEWARE: to not import this package outside the function
    # Otherwise pip will go crazy
    # (we cannot understand why, but it does!)
    from controller.packages import install, check_version

    log.info("You asked to install rapydo-controller {} from git", version)

    package = "rapydo-controller"
    controller_repository = "do"
    rapydo_uri = "https://github.com/rapydo"
    controller = "git+{}/{}.git@{}".format(rapydo_uri, controller_repository, version)

    installed = install(controller, user=user)

    if not installed:
        log.error("Unable to install controller {} from git", version)
    else:
        log.info("Controller version {} installed from git", version)
        installed_version = check_version(package)
        log.info("Check on installed version: {}", installed_version)


def install_controller_from_folder(gits, version, user, editable):

    # BEWARE: to not import this package outside the function
    # Otherwise pip will go crazy
    # (we cannot understand why, but it does!)
    from controller.packages import install, check_version

    log.info("You asked to install rapydo-controller {} from local folder", version)

    do_path = os.path.join(SUBMODULES_DIR, "do")
    if not os.path.exists(do_path):
        log.exit("{} path not found", do_path)

    do_repo = gits.get('do')

    b = gitter.get_active_branch(do_repo)

    if b is None:
        log.error("Unable to read local controller repository")
    elif b == version:
        log.info("Controller repository already at {}", version)
    elif gitter.switch_branch(do_repo, version):
        log.info("Controller repository switched to {}", version)
    else:
        log.exit("Invalid version")

    installed = install(do_path, editable=editable, user=user)

    if not installed:
        log.error("Unable to install controller {} from local folder", version)
    else:
        log.info("Controller version {} installed from local folder", version)
        installed_version = check_version("rapydo-controller")
        log.info("Check on installed version: {}", installed_version)


def __call__(args, rapydo_version, gits, **kwargs):

    version = args.get('version')
    pip = args.get('pip')
    editable = args.get('editable')
    local = args.get('local')
    user = args.get('user')

    if pip and editable:
        log.exit("--pip and --editable options are not compatible")
    if pip and local:
        log.exit("--pip and --local options are not compatible")
    if user and editable:
        log.exit("--user and --editable options are not compatible")

    if version == 'auto':
        version = rapydo_version
        log.info("Detected version {} to be installed", version)

    if editable or local:
        return install_controller_from_folder(gits, version, user, editable)
    elif pip:
        return install_controller_from_pip(version, user)
    else:
        return install_controller_from_git(version, user)
