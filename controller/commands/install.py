"""
Install the specified version of RAPyDO or docker, compose, buildx
"""
import typer

from controller import SUBMODULES_DIR, log, print_and_exit
from controller.app import Application, Configuration
from controller.packages import Packages
from controller.utilities import git


@Application.app.command(help="Install the specified version of rapydo")
def install(
    version: str = typer.Argument("auto", help="Version to be installed"),
    editable: bool = typer.Option(
        True,
        "--no-editable",
        help="Disable editable mode",
        show_default=False,
    ),
) -> None:

    Application.print_command(
        Application.serialize_parameter("--no-editable", not editable, IF=not editable),
        Application.serialize_parameter("", version),
    )

    if version == "docker":
        Packages.install_docker()
        return None

    if version == "compose":
        Packages.install_compose()
        return None

    if version == "buildx":
        Packages.install_buildx()
        return None

    Application.get_controller().controller_init()

    if version == "auto":
        version = Configuration.rapydo_version
        log.info("Detected version {} to be installed", version)

    if editable:
        install_controller_from_folder(version)
    else:
        install_controller_from_git(version)


def install_controller_from_folder(version: str) -> None:

    do_path = SUBMODULES_DIR.joinpath("do")
    try:
        Application.git_submodules()
    except SystemExit:

        log.info(
            """You asked to install rapydo {ver} in editable mode, but {p} is missing.

You can force the installation by disabling the editable mode:

rapydo install {ver} --no-editable

""",
            ver=version,
            p=do_path,
        )

        raise

    log.info(
        "You asked to install rapydo {}. It will be installed in editable mode",
        version,
    )

    do_repo = Application.gits.get("do")

    b = git.get_active_branch(do_repo)

    if b is None:
        log.error("Unable to read local controller repository")  # pragma: no cover
    elif b == version:
        log.info("Controller repository already at {}", version)
    elif git.switch_branch(do_repo, version):
        log.info("Controller repository switched to {}", version)
    else:
        print_and_exit("Invalid version")

    Packages.install(do_path, editable=True)
    log.info("Controller version {} installed from local folder", version)


def install_controller_from_git(version: str) -> None:

    controller = f"git+https://github.com/rapydo/do.git@{version}"

    log.info("You asked to install rapydo {} from git", version)

    Packages.install(controller, editable=False)
    log.info("Controller version {} installed from git", version)
