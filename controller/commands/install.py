import hashlib
import stat
import tempfile
import time
from pathlib import Path

import requests
import typer
from python_on_whales import docker
from sultan.api import Sultan

from controller import SUBMODULES_DIR, log, print_and_exit
from controller.app import Application, Configuration
from controller.packages import Packages
from controller.utilities import git

# https://get.docker.com
EXPECTED_DOCKER_SCRIPT_MD5 = "dd5da5e89bf5730e84ef5b20dc45588c"

# https://github.com/docker/compose/releases
COMPOSE_VERSION = "v2.1.0"
EXPECTED_COMPOSE_BIN_MD5 = "36360ac1955f1e7be79a8b63532f4ffd"

# https://github.com/docker/buildx/releases
BUILDX_VERSION = "v0.6.3"
EXPECTED_BUILDX_BIN_MD5 = "1b3bcb477b47d2251389402d57221f6f"


def download(url: str, expected_checksum: str) -> Path:
    try:
        r = requests.get(url, timeout=10)
        if r.status_code != 200:
            print_and_exit(
                "Can't download {}, invalid status code {}", url, str(r.status_code)
            )

        file: Path = Path(tempfile.NamedTemporaryFile().name)

        with open(file, "wb") as f:
            for chunk in r.iter_content(chunk_size=1024):
                if chunk:  # filter out keep-alive new chunks
                    f.write(chunk)

        md5 = hashlib.md5(open(file, "rb").read()).hexdigest()
        if md5 == expected_checksum:
            log.info("Checksum verified: {}", md5)
        else:
            print_and_exit(
                "Checksum of download file ({}) does not match the expected value ({})",
                md5,
                expected_checksum,
            )

        return file
    except requests.exceptions.ReadTimeout as e:  # pragma: no cover
        print_and_exit("The request timed out, please retry in a while ({})", str(e))


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
        log.info("Docker current version: {}", Packages.get_bin_version("docker"))
        url = "https://get.docker.com"
        log.info("Downloading installation script: {}", url)
        f = download(url, EXPECTED_DOCKER_SCRIPT_MD5)

        log.info("The installation script contains a wait, please be patient")
        with Sultan.load(sudo=True) as sultan:
            result = sultan.sh(f).run()

            for r in result.stdout + result.stderr:
                print(r)

        log.info("Docker installed version: {}", Packages.get_bin_version("docker"))
        return None

    if version == "compose":
        cli_plugin = Path.home().joinpath(".docker", "cli-plugins")
        cli_plugin.mkdir(parents=True, exist_ok=True)
        compose_bin = cli_plugin.joinpath("docker-compose")

        url = "https://github.com/docker/compose/releases/download/"
        url += f"{COMPOSE_VERSION}/docker-compose-linux-x86_64"

        log.info("Downloading compose binary: {}", url)
        f = download(url, EXPECTED_COMPOSE_BIN_MD5)
        f.rename(compose_bin)
        compose_bin.chmod(compose_bin.stat().st_mode | stat.S_IEXEC)

        if docker.compose.is_installed():
            log.info("Docker compose is installed")
        else:  # pragma: no cover
            log.error("Docker compose is NOT installed")
        return None

    if version == "buildx":
        if docker.buildx.is_installed():
            v = docker.buildx.version()
            log.info("Docker buildx current version: {}", v)
        else:  # pragma: no cover
            log.info("Docker buildx current version: N/A")

        cli_plugin = Path.home().joinpath(".docker", "cli-plugins")
        cli_plugin.mkdir(parents=True, exist_ok=True)
        buildx_bin = cli_plugin.joinpath("docker-buildx")

        url = "https://github.com/docker/buildx/releases/download/"
        url += f"{BUILDX_VERSION}/buildx-{BUILDX_VERSION}.linux-amd64"

        log.info("Downloading buildx binary: {}", url)
        f = download(url, EXPECTED_BUILDX_BIN_MD5)

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
        print_and_exit("Invalid version")

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
