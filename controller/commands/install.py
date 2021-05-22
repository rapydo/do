import time

import typer

from controller import SUBMODULES_DIR, gitter, log
from controller.app import Application, Configuration
from controller.packages import Packages


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
        """You asked to install rapydo {}. It will be installed in editable mode

This command will require root privileges because of the editable mode.
You could be prompted to enter your password: this is due to the use of sudo.

If you want to execute this installation by yourself, you can execute:

sudo pip3 install --upgrade --editable {}
""",
        version,
        do_path,
    )

    time.sleep(2)

    do_repo = Application.gits.get("do")

    b = gitter.get_active_branch(do_repo)

    if b is None:
        log.error("Unable to read local controller repository")  # pragma: no cover
    elif b == version:
        log.info("Controller repository already at {}", version)
    elif gitter.switch_branch(do_repo, version):
        log.info("Controller repository switched to {}", version)
    else:
        Application.exit("Invalid version")

    installed = Packages.install(do_path, editable=True, user=False)

    if not installed:  # pragma: no cover
        log.error("Unable to install controller {} from local folder", version)
    else:
        log.info("Controller version {} installed from local folder", version)


def install_controller_from_git(version: str) -> None:

    controller_repository = "do"
    rapydo_uri = "https://github.com/rapydo"
    controller = f"git+{rapydo_uri}/{controller_repository}.git@{version}"

    log.info(
        """You asked to install rapydo {} from git. It will be installed globally

This command will require root privileges because of the global installation.
You could be prompted to enter your password: this is due to the use of sudo.

If you want to execute this installation by yourself, you can execute:

sudo pip3 install --upgrade [--user] {}


""",
        version,
        controller,
    )

    time.sleep(2)

    installed = Packages.install(controller, user=False)

    if not installed:  # pragma: no cover
        log.error("Unable to install controller {} from git", version)
    else:
        log.info("Controller version {} installed from git", version)
