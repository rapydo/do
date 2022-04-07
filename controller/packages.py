"""
Utilities to work with python packages and binaries
"""

# BEWARE: to not import this package at startup,
# but only into functions otherwise pip will go crazy
# (we cannot understand why, but it does!)
import os
import re
from pathlib import Path
from typing import List, Optional, Union

from packaging.version import Version
from sultan.api import Sultan

from controller import RED, log, print_and_exit
from controller.utilities import system


class Packages:
    @staticmethod
    def install(package: Union[str, Path], editable: bool) -> bool:
        """
        Install a python package in editable or normal mode
        """
        # Note: package is a Path if editable, str otherwise

        try:

            with Sultan.load(sudo=False) as sultan:
                command = "install --upgrade"

                if editable:
                    command += " --prefix $HOME/.local"
                    command += " --editable"
                else:
                    command += " --user"

                command += f" {package}"

                result = sultan.pip3(command).run()

                for r in result.stdout + result.stderr:
                    print(r)

                return bool(result.rc == 0)
        except Exception as e:  # pragma: no cover
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
        cls, exec_cmd: str, option: List[str] = ["--version"]
    ) -> Optional[str]:
        """
        Retrieve the version of a binary
        """

        try:

            if os.name == "nt":  # pragma: no cover
                exec_cmd = cls.convert_bin_to_win32(exec_cmd)

            output = system.execute_command(exec_cmd, option)

            # then last element on spaces
            # get up to the first open round bracket if any, or return the whole string
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
            # Note that in may other cases it fails...
            # but we are interested in a very small list of programs, so it's ok
            # echo --version -> --version
            # ls --version -> ls
            # pip3 --version -> a path
        except system.ExecutionException as e:
            log.error(e)

        return None

    @staticmethod
    def get_installation_path(package: str = "rapydo") -> Optional[Path]:
        """
        Retrieve the controller installation path, if installed in editable mode
        """
        command = "list --editable"

        with Sultan.load(sudo=False) as sultan:

            result = sultan.pip3(command).run()

            for r in result.stdout + result.stderr:
                if r.startswith(f"{package} "):
                    tokens = re.split(r"\s+", r)
                    return Path(str(tokens[2]))

        return None
