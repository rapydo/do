import os

import typer

from controller import SUBMODULES_DIR, gitter, log
from controller.app import Application
from controller.packages import Packages


@Application.app.command(help="Install specified version of rapydo-controller")
def install(
    version: str = typer.Argument("auto", help="Version to be installed"),
    pip: bool = typer.Option(
        False, "--pip", help="Install from pypi", show_default=False,
    ),
    editable: bool = typer.Option(
        False,
        "--editable",
        help="Install in editable mode from submodules folder",
        show_default=False,
    ),
    user: bool = typer.Option(
        False,
        "--user",
        help="Install at user level (sudo not required)",
        show_default=False,
    ),
):

    if pip and editable:
        log.exit("--pip and --editable options are not compatible")
    if user and editable:
        log.exit("--user and --editable options are not compatible")

    if version == "auto":
        version = Application.data.rapydo_version
        log.info("Detected version {} to be installed", version)

    if editable:
        return install_controller_from_folder(
            Application.data.gits, version, user, editable
        )
    elif pip:
        return install_controller_from_pip(version, user)
    else:
        return install_controller_from_git(version, user)


def install_controller_from_pip(version, user):

    log.info("You asked to install rapydo-controller {} from pip", version)

    package = "rapydo-controller"
    controller = f"{package}=={version}"
    installed = Packages.install(controller, user=user)
    if not installed:  # pragma: no cover
        log.error("Unable to install controller {} from pip", version)
    else:
        log.info("Controller version {} installed from pip", version)


def install_controller_from_git(version, user):

    log.info("You asked to install rapydo-controller {} from git", version)

    package = "rapydo-controller"
    controller_repository = "do"
    rapydo_uri = "https://github.com/rapydo"
    controller = f"git+{rapydo_uri}/{controller_repository}.git@{version}"

    installed = Packages.install(controller, user=user)

    if not installed:  # pragma: no cover
        log.error("Unable to install controller {} from git", version)
    else:
        log.info("Controller version {} installed from git", version)
        installed_version = Packages.check_version(package)
        log.info("Check on installed version: {}", installed_version)


def install_controller_from_folder(gits, version, user, editable):

    log.info("You asked to install rapydo-controller {} from local folder", version)

    do_path = os.path.join(SUBMODULES_DIR, "do")

    do_repo = gits.get("do")

    b = gitter.get_active_branch(do_repo)

    if b is None:
        log.error("Unable to read local controller repository")  # pragma: no cover
    elif b == version:
        log.info("Controller repository already at {}", version)
    elif gitter.switch_branch(do_repo, version):
        log.info("Controller repository switched to {}", version)
    else:
        log.exit("Invalid version")

    installed = Packages.install(do_path, editable=editable, user=user)

    if not installed:  # pragma: no cover
        log.error("Unable to install controller {} from local folder", version)
    else:
        log.info("Controller version {} installed from local folder", version)
        installed_version = Packages.check_version("rapydo-controller")
        log.info("Check on installed version: {}", installed_version)
