# BEWARE: to not import this package at startup,
# but only into functions otherwise pip will go crazy
# (we cannot understand why, but it does!)
import re
import sys
from distutils.version import LooseVersion
from importlib import import_module
from pathlib import Path
from types import ModuleType
from typing import List, Optional, Union

from sultan.api import Sultan

from controller import log
from controller.utilities import system


class Packages:
    @staticmethod
    def install(
        # Path if editable, str otherwise
        package: Union[str, Path],
        editable: bool = False,
        user: bool = False,
        use_pip3: bool = True,
    ) -> bool:

        # Do not import outside, otherwise it will lead to a circular import:
        # cannot import name 'Configuration' from partially initialized module
        from controller.app import Configuration

        if use_pip3 and Packages.get_bin_version("pip3") is None:  # pragma: no cover
            return Packages.install(
                package=package, editable=editable, user=user, use_pip3=False
            )

        try:
            sudo = not user
            # sudo does not work on travis
            if Configuration.testing:
                sudo = False

            with Sultan.load(sudo=sudo) as sultan:
                command = "install --upgrade"
                # --user does not work on travis:
                # Can not perform a '--user' install.
                # User site-packages are not visible in this virtualenv.
                if not Configuration.testing and user:  # pragma: no cover
                    command += " --user"
                if editable:
                    command += " --editable"
                command += f" {package}"

                pip = sultan.pip3 if use_pip3 else sultan.pip
                result = pip(command).run()

                for r in result.stdout + result.stderr:
                    print(r)

                return bool(result.rc == 0)
        except BaseException as e:  # pragma: no cover
            log.critical(e)
            sys.exit(1)

    @staticmethod
    def import_package(package_name: str) -> Optional[ModuleType]:

        try:
            return import_module(package_name)
        except (ModuleNotFoundError, ImportError):
            return None

    @staticmethod
    def package_version(package_name: str) -> Optional[str]:
        package = Packages.import_package(package_name)
        if package is None:
            return None
        return str(package.__version__)  # type: ignore

    @staticmethod
    def check_python_package(
        package_name: str,
        min_version: Optional[str] = None,
        max_version: Optional[str] = None,
    ) -> Optional[str]:

        found_version = Packages.package_version(package_name)
        if found_version is None:
            log.critical(
                "Could not find the following python package: {}", package_name
            )
            sys.exit(1)

        try:
            if min_version is not None:
                if LooseVersion(min_version) > LooseVersion(found_version):
                    log.critical(
                        "Minimum supported version for {} is {}, found {}",
                        package_name,
                        min_version,
                        found_version,
                    )
                    sys.exit(1)

            if max_version is not None:
                if LooseVersion(max_version) < LooseVersion(found_version):
                    log.critical(
                        "Maximum supported version for {} is {}, found {}",
                        package_name,
                        max_version,
                        found_version,
                    )
                    sys.exit(1)

            log.debug("{} version: {}", package_name, found_version)
            return found_version
        except TypeError as e:  # pragma: no cover
            log.error("{}: {}", e, found_version)
            return None

    @staticmethod
    def check_program(
        program: str,
        min_version: Optional[str] = None,
        max_version: Optional[str] = None,
        min_recommended_version: Optional[str] = None,
    ) -> str:

        found_version = Packages.get_bin_version(program)
        if found_version is None:

            hints = ""
            if program == "docker":  # pragma: no cover
                hints = "\n\nTo install docker visit: https://get.docker.com"

            log.critical(
                "A mandatory dependency is missing: {} not found{}", program, hints
            )
            sys.exit(1)

        v = LooseVersion(found_version)
        if min_version is not None:
            if LooseVersion(min_version) > v:
                log.critical(
                    "Minimum supported version for {} is {}, found {}",
                    program,
                    min_version,
                    found_version,
                )
                sys.exit(1)

        if min_recommended_version is not None:
            if LooseVersion(min_recommended_version) > v:
                log.warning(
                    "Minimum recommended version for {} is {}, found {}",
                    program,
                    min_recommended_version,
                    found_version,
                )

        if max_version is not None:
            if LooseVersion(max_version) < v:
                log.critical(
                    "Maximum supported version for {} is {}, found {}",
                    program,
                    max_version,
                    found_version,
                )
                sys.exit(1)

        log.debug("{} version: {}", program, found_version)
        return found_version

    @staticmethod
    def get_bin_version(
        exec_cmd: str, option: List[str] = ["--version"]
    ) -> Optional[str]:

        try:
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
    def get_installation_path(
        package: str = "rapydo", use_pip3: bool = True
    ) -> Optional[Path]:
        command = "list --editable"

        with Sultan.load(sudo=False) as sultan:
            pip = sultan.pip3 if use_pip3 else sultan.pip
            result = pip(command).run()

            for r in result.stdout + result.stderr:
                if r.startswith(f"{package} "):
                    tokens = re.split(r"\s+", r)
                    return Path(str(tokens[2]))
        return None
