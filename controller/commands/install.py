from typing import Any, Optional

import typer

from controller import SUBMODULES_DIR, gitter, log
from controller.app import Application, Configuration
from controller.packages import Packages


@Application.app.command(help="Install specified version of rapydo")
def install(
    version: Optional[str] = typer.Argument("auto", help="Version to be installed"),
    editable: bool = typer.Option(
        True,
        "--no-editable",
        help="Disable editable mode",
        show_default=False,
    ),
) -> Any:
    Application.get_controller().controller_init()

    if version == "auto":
        version = Configuration.rapydo_version
        log.info("Detected version {} to be installed", version)

    user_mode = not editable
    if editable:
        return install_controller_from_folder(
            Application.gits, version, user_mode, editable
        )

    else:
        return install_controller_from_git(version, user_mode)


def install_controller_from_folder(gits, version, user, editable):

    Application.git_submodules()

    log.info("You asked to install rapydo {} from local folder", version)

    do_path = SUBMODULES_DIR.joinpath("do")

    do_repo = gits.get("do")

    b = gitter.get_active_branch(do_repo)

    if b is None:
        log.error("Unable to read local controller repository")  # pragma: no cover
    elif b == version:
        log.info("Controller repository already at {}", version)
    elif gitter.switch_branch(do_repo, version):
        log.info("Controller repository switched to {}", version)
    else:
        Application.exit("Invalid version")

    installed = Packages.install(do_path, editable=editable, user=user)

    if not installed:  # pragma: no cover
        log.error("Unable to install controller {} from local folder", version)
    else:
        log.info("Controller version {} installed from local folder", version)


def install_controller_from_git(version, user):

    log.info("You asked to install rapydo {} from git", version)

    controller_repository = "do"
    rapydo_uri = "https://github.com/rapydo"
    controller = f"git+{rapydo_uri}/{controller_repository}.git@{version}"

    installed = Packages.install(controller, user=user)

    if not installed:  # pragma: no cover
        log.error("Unable to install controller {} from git", version)
    else:
        log.info("Controller version {} installed from git", version)
