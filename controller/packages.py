"""
Utilities to work with python packages and binaries
"""

# WARNING: to not import this package at startup,
# but only into functions otherwise pip will go crazy
# (we cannot understand why, but it does!)

import hashlib
import os
import re
import stat
import sys
import tempfile
from pathlib import Path
from typing import List, Optional, Union

import requests
from packaging.version import Version
from plumbum import local  # type: ignore
from plumbum.commands.processes import (  # type: ignore
    CommandNotFound,
    ProcessExecutionError,
)
from python_on_whales import docker
from sultan.api import Sultan  # type: ignore

from controller import RED, log, print_and_exit

# https://get.docker.com
EXPECTED_DOCKER_SCRIPT_MD5 = "21991ad5158db696823e3fd54eab00da"

# https://github.com/docker/compose/releases
COMPOSE_VERSION = "v2.24.6"
EXPECTED_COMPOSE_LINUX_BIN_MD5 = "593fb55fe05a76d5c5efb383e91ba129"
EXPECTED_COMPOSE_MACOS_BIN_MD5 = "e9b48a919560f33710530ef6f18e26a1"
EXPECTED_COMPOSE_WIN_BIN_MD5 = "not-implemented"

# https://github.com/docker/buildx/releases
BUILDX_VERSION = "v0.13.1"
EXPECTED_BUILDX_LINUX_BIN_MD5 = "c7145e327f600f8e960f74f336926ecd"
EXPECTED_BUILDX_MACOS_BIN_MD5 = "71a155d9a6f20510e2b7df0298e6291b"
EXPECTED_BUILDX_WIN_BIN_MD5 = "not-implemented"

DEFAULT_PIP_BIN = "pip3"
ALTERNATIVE_PIP_BIN = "pip"


class ExecutionException(Exception):
    pass


class Packages:
    @staticmethod
    def install(
        package: Union[str, Path], editable: bool, pip_bin: str = DEFAULT_PIP_BIN
    ) -> None:
        """
        Install a python package in editable or normal mode
        """

        try:
            options = ["install", "--upgrade"]

            home = Path.home()

            if editable:
                if sys.platform != "darwin" and sys.platform != "win32":
                    options.append("--prefix")
                    options.append(f"{home}/.local")
                options.append("--editable")
            else:
                options.append("--user")

            # Note: package is a Path if editable, str otherwise
            options.append(str(package))

            output = Packages.execute_command(pip_bin, options)

            for r in output.split("\n"):
                print(r)

        except Exception as e:  # pragma: no cover
            if pip_bin == DEFAULT_PIP_BIN:
                return Packages.install(package, editable, pip_bin=ALTERNATIVE_PIP_BIN)
            print_and_exit(str(e))

    @staticmethod
    def check_program(
        program: str,
        min_version: Optional[str] = None,
        max_version: Optional[str] = None,
        min_recommended_version: Optional[str] = None,
    ) -> str:
        """
        Verify if a binary exists and (optionally) its version
        """

        found_version = Packages.get_bin_version(program)
        if found_version is None:
            hints = ""
            if program == "docker":  # pragma: no cover
                install_cmd = RED("rapydo install docker")
                hints = "\n\nTo install docker visit: https://get.docker.com"
                hints += f"or execute {install_cmd}"

            print_and_exit(
                "A mandatory dependency is missing: {} not found{}", program, hints
            )

        v = Version(found_version)
        if min_version is not None:
            if Version(min_version) > v:
                print_and_exit(
                    "Minimum supported version for {} is {}, found {}",
                    program,
                    min_version,
                    found_version,
                )

        if min_recommended_version is not None:
            if Version(min_recommended_version) > v:
                log.warning(
                    "Minimum recommended version for {} is {}, found {}",
                    program,
                    min_recommended_version,
                    found_version,
                )

        if max_version is not None:
            if Version(max_version) < v:
                print_and_exit(
                    "Maximum supported version for {} is {}, found {}",
                    program,
                    max_version,
                    found_version,
                )

        log.debug("{} version: {}", program, found_version)
        return found_version

    @staticmethod
    def convert_bin_to_win32(exec_cmd: str) -> str:
        """
        Convert a binary name to Windows standards
        """
        if exec_cmd == "docker":
            return "docker.exe"
        return exec_cmd

    @classmethod
    def get_bin_version(
        cls,
        exec_cmd: str,
        option: Optional[List[str]] = None,
        clean_output: bool = True,
    ) -> Optional[str]:
        """
        Retrieve the version of a binary
        """

        if option is None:
            option = ["--version"]

        try:
            if os.name == "nt":  # pragma: no cover
                exec_cmd = cls.convert_bin_to_win32(exec_cmd)

            output = Packages.execute_command(exec_cmd, option)

            if clean_output:
                # then last element on spaces
                # get up to the first open round bracket if any,
                # or return the whole string
                output = output.split("(")[0]
                # get up to the first comma if any, or return the whole string
                output = output.split(",")[0]
                # split on spaces and take the last element
                output = output.split()[-1]
                # Remove trailing spaces
                output = output.strip()
                # Removed single quotes
                output = output.replace("'", "")

            # That's all... this magic receipt is able to extract
            # version information from most of outputs, e.g.
            # Python 3.8.2
            # Docker version 19.03.8, build afacb8b7f0
            # git version 2.25.1
            # rapydo version 0.7.x
            return output
            # Note that in many other cases it fails...
            # but we are interested in a very small list of programs, so it's ok
            # echo --version -> --version
            # ls --version -> ls
            # pip3 --version -> a path
        except ExecutionException as e:
            log.error(e)

        return None

    @staticmethod
    def get_installation_path(
        package: str = "rapydo", pip_bin: str = DEFAULT_PIP_BIN
    ) -> Optional[Path]:
        """
        Retrieve the controller installation path, if installed in editable mode
        """
        try:
            for r in Packages.execute_command(pip_bin, ["list", "--editable"]).split(
                "\n"
            ):
                if r.startswith(f"{package} "):
                    tokens = re.split(r"\s+", r)
                    return Path(str(tokens[2]))
        except Exception as e:  # pragma: no cover
            if pip_bin == DEFAULT_PIP_BIN:
                return Packages.get_installation_path(
                    package, pip_bin=ALTERNATIVE_PIP_BIN
                )
            print_and_exit(str(e))

        return None

    @staticmethod
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

            md5 = "N/A"
            with open(file, "rb") as f:
                md5 = hashlib.md5(f.read()).hexdigest()

            if md5 == expected_checksum:
                log.info("Checksum verified: {}", md5)
            else:
                print_and_exit(
                    "File checksum ({}) does not match the expected value ({})",
                    md5,
                    expected_checksum,
                )

            return file
        except requests.exceptions.ReadTimeout as e:  # pragma: no cover
            print_and_exit(
                "The request timed out, please retry in a while ({})", str(e)
            )

    @staticmethod
    def install_docker() -> None:
        log.info("Docker current version: {}", Packages.get_bin_version("docker"))
        url = "https://get.docker.com"
        log.info("Downloading installation script: {}", url)
        f = Packages.download(url, EXPECTED_DOCKER_SCRIPT_MD5)

        log.info("The installation script contains a wait, please be patient")
        with Sultan.load(sudo=True) as sultan:
            result = sultan.sh(f).run()

            for r in result.stdout + result.stderr:
                print(r)

        log.info("Docker installed version: {}", Packages.get_bin_version("docker"))

    @staticmethod
    def install_compose() -> None:
        cli_plugin = Path.home().joinpath(".docker", "cli-plugins")
        cli_plugin.mkdir(parents=True, exist_ok=True)
        compose_bin = cli_plugin.joinpath("docker-compose")

        if sys.platform == "darwin":  # pragma: no cover
            bin_name = "docker-compose-darwin-x86_64"
            expected_compose_bin_md5 = EXPECTED_COMPOSE_MACOS_BIN_MD5
        elif sys.platform == "win32":  # pragma: no cover
            bin_name = "docker-compose-windows-x86_64.exe"
            expected_compose_bin_md5 = EXPECTED_COMPOSE_WIN_BIN_MD5
        else:
            bin_name = "docker-compose-linux-x86_64"
            expected_compose_bin_md5 = EXPECTED_COMPOSE_LINUX_BIN_MD5

        url = "https://github.com/docker/compose/releases/download/"
        url += f"{COMPOSE_VERSION}/{bin_name}"

        log.info("Downloading compose binary: {}", url)
        f = Packages.download(url, expected_compose_bin_md5)
        f.rename(compose_bin)
        compose_bin.chmod(compose_bin.stat().st_mode | stat.S_IEXEC)

        if docker.compose.is_installed():
            log.info("Docker compose is installed")
        else:  # pragma: no cover
            log.error("Docker compose is NOT installed")

    @staticmethod
    def install_buildx() -> None:
        if docker.buildx.is_installed():
            v = docker.buildx.version()
            log.info("Docker buildx current version: {}", v)
        else:  # pragma: no cover
            log.info("Docker buildx current version: N/A")

        cli_plugin = Path.home().joinpath(".docker", "cli-plugins")
        cli_plugin.mkdir(parents=True, exist_ok=True)
        buildx_bin = cli_plugin.joinpath("docker-buildx")

        if sys.platform == "darwin":  # pragma: no cover
            # Intel CPU
            # bin_name = f"buildx-{BUILDX_VERSION}.darwin-amd64"
            # Apple CPU
            bin_name = f"buildx-{BUILDX_VERSION}.darwin-arm64"
            expected_compose_bin_md5 = EXPECTED_BUILDX_MACOS_BIN_MD5
        elif sys.platform == "win32":  # pragma: no cover
            bin_name = f"buildx-{BUILDX_VERSION}.windows-amd64.exe"
            expected_compose_bin_md5 = EXPECTED_BUILDX_WIN_BIN_MD5
        else:
            bin_name = f"buildx-{BUILDX_VERSION}.linux-amd64"
            expected_compose_bin_md5 = EXPECTED_BUILDX_LINUX_BIN_MD5

        url = "https://github.com/docker/buildx/releases/download/"
        url += f"{BUILDX_VERSION}/{bin_name}"

        log.info("Downloading buildx binary: {}", url)
        f = Packages.download(url, expected_compose_bin_md5)

        f.rename(buildx_bin)
        buildx_bin.chmod(buildx_bin.stat().st_mode | stat.S_IEXEC)

        v = docker.buildx.version()
        log.info("Docker buildx installed version: {}", v)

    @staticmethod
    def execute_command(command: str, parameters: List[str]) -> str:
        try:
            # Pattern in plumbum library for executing a shell command
            local_command = local[command]
            log.info("Executing command {} {}", command, " ".join(parameters))
            return str(local_command(parameters))
        except CommandNotFound as e:
            raise ExecutionException(f"Command not found: {command}") from e

        except ProcessExecutionError as e:
            raise ExecutionException(
                f"Cannot execute command: {command} {' '.join(parameters)}"
            ) from e

        # raised on Windows
        except OSError as e:  # pragma: no cover
            raise ExecutionException(f"Cannot execute: {command}: {e}") from e
