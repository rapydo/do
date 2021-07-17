import stat
import tempfile
import time
from pathlib import Path

import requests
import typer
from python_on_whales import docker
from python_on_whales.utils import DockerException
from sultan.api import Sultan

from controller import SUBMODULES_DIR, log
from controller.app import Application, Configuration
from controller.packages import Packages
from controller.utilities import git

# https://github.com/docker/compose-cli/releases
COMPOSE_VERSION = "v2.0.0-beta.6"
# https://github.com/docker/buildx/releases
BUILDX_VERSION = "v0.6.0"


def download(url: str) -> Path:
    r = requests.get(url)
    if r.status_code != 200:
        Application.exit(
            "Can't download {}, invalid status code {}", url, str(r.status_code)
        )

    file: Path = Path(tempfile.NamedTemporaryFile().name)

    with open(file, "wb") as f:
        for chunk in r.iter_content(chunk_size=1024):
            if chunk:  # filter out keep-alive new chunks
                f.write(chunk)

    return file


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

    if version == "docker":
        log.info("Docker current version: {}", Packages.get_bin_version("docker"))
        url = "https://get.docker.com"
        f = download(url)
        log.info("The installation script contains a wait, please be patient")
        with Sultan.load(sudo=True) as sultan:
            result = sultan.sh(f).run()

            for r in result.stdout + result.stderr:
                print(r)

        log.info("Docker installed version: {}", Packages.get_bin_version("docker"))
        return None

    if version == "compose":
        f = download(
            "https://raw.githubusercontent.com/docker/compose-cli/main/scripts/install/install_linux.sh"
        )
        with Sultan.load(sudo=True) as sultan:
            result = sultan.sh(f).run()

            for r in result.stdout + result.stderr:
                print(r)

        cli_plugin = Path.home().joinpath(".docker", "cli-plugins")
        cli_plugin.mkdir(parents=True, exist_ok=True)
        compose_bin = cli_plugin.joinpath("docker-compose")

        url = "https://github.com/docker/compose-cli/releases/download/"
        url += f"{COMPOSE_VERSION}/docker-compose-linux-amd64"

        f = download(url)
        f.rename(compose_bin)
        compose_bin.chmod(compose_bin.stat().st_mode | stat.S_IEXEC)

        if docker.compose.is_installed():
            log.info("Docker compose is installed")
        else:  # pragma: no cover
            log.error("Docker compose is NOT installed")
        return None

    if version == "buildx":

        try:
            v = docker.buildx.version()
            log.info("Docker buildx current version: {}", v)
        except DockerException as e:  # pragma: no cover
            log.critical("Raised exception is: {}", type(e))
            log.info("Docker buildx current version: N/A")

        cli_plugin = Path.home().joinpath(".docker", "cli-plugins")
        cli_plugin.mkdir(parents=True, exist_ok=True)
        buildx_bin = cli_plugin.joinpath("docker-buildx")

        url = "https://github.com/docker/buildx/releases/download/"
        url += f"{BUILDX_VERSION}/buildx-{BUILDX_VERSION}.linux-amd64"

        f = download(url)
        f.rename(buildx_bin)
        buildx_bin.chmod(buildx_bin.stat().st_mode | stat.S_IEXEC)

        v = docker.buildx.version()
        log.info("Docker buildx installed version: {}", v)
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

    b = git.get_active_branch(do_repo)

    if b is None:
        log.error("Unable to read local controller repository")  # pragma: no cover
    elif b == version:
        log.info("Controller repository already at {}", version)
    elif git.switch_branch(do_repo, version):
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
