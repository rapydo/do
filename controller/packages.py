# BEWARE: to not import this package at startup,
# but only into functions otherwise pip will go crazy
# (we cannot understand why, but it does!)

# which version of python is this?
# Retrocompatibility for Python < 3.6
from distutils.version import LooseVersion
from importlib import import_module

from sultan.api import Sultan

from controller import log
from controller.utilities import system


class Packages:
    @staticmethod
    def install(package, editable=False, user=False, use_pip3=True):

        # Do not import outside, otherwise:
        # cannot import name 'Configuration' from partially initialized module
        # most likely due to a circular import
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

                return result.rc == 0
        except BaseException as e:  # pragma: no cover
            log.exit(e)

    @staticmethod
    def check_version(package_name):

        # Don't import before or pip will mess up everything! Really crazy
        from pip._internal.utils.misc import get_installed_distributions

        for pkg in get_installed_distributions(local_only=True, user_only=False):
            if pkg._key == package_name:  # pylint:disable=protected-access
                return pkg._version  # pylint:disable=protected-access

        return None

    @staticmethod
    def import_package(package_name):

        try:
            return import_module(package_name)
        except (ModuleNotFoundError, ImportError):
            return None

    @staticmethod
    def package_version(package_name):
        package = Packages.import_package(package_name)
        if package is None:
            return None
        return package.__version__

    @staticmethod
    def check_python_package(package_name, min_version=None, max_version=None):

        found_version = Packages.package_version(package_name)
        if found_version is None:  # pragma: no cover
            log.exit("Could not find the following python package: {}", package_name)
        try:
            if min_version is not None:  # pragma: no cover
                if LooseVersion(min_version) > LooseVersion(found_version):
                    version_error = "Minimum supported version for {} is {}".format(
                        package_name, min_version
                    )
                    version_error += f", found {found_version} "
                    log.exit(version_error)

            if max_version is not None:  # pragma: no cover
                if LooseVersion(max_version) < LooseVersion(found_version):
                    version_error = "Maximum supported version for {} is {}".format(
                        package_name, max_version
                    )
                    version_error += f", found {found_version} "
                    log.exit(version_error)

            log.debug("{} version: {}", package_name, found_version)
            return found_version
        except TypeError as e:  # pragma: no cover
            log.error("{}: {}", e, found_version)

    @staticmethod
    def check_program(program, min_version=None, max_version=None):

        found_version = Packages.get_bin_version(program)
        # Can't be tested on travis...
        if found_version is None:  # pragma: no cover

            hints = ""
            if program == "docker":
                hints = "\n\nTo install docker visit: https://get.docker.com"

            log.exit("Missing requirement: {} not found.{}", program, hints)

        if min_version is not None:  # pragma: no cover
            if LooseVersion(min_version) > LooseVersion(found_version):
                version_error = "Minimum supported version for {} is {}".format(
                    program,
                    min_version,
                )
                version_error += f", found {found_version} "
                log.exit(version_error)

        if max_version is not None:  # pragma: no cover
            if LooseVersion(max_version) < LooseVersion(found_version):
                version_error = "Maximum supported version for {} is {}".format(
                    program,
                    max_version,
                )
                version_error += f", found {found_version} "
                log.exit(version_error)

        log.debug("{} version: {}", program, found_version)
        return found_version

    @staticmethod
    def get_bin_version(exec_cmd, option="--version"):

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
    def check_docker_vulnerability():

        # Check for CVE-2019-5736 vulnerability
        # Checking version of docker server, since docker client is not affected
        # and the two versions can differ
        v = Packages.get_bin_version(
            "docker", option=["version", "--format", "'{{.Server.Version}}'"]
        )

        if v is None:  # pragma: no cover
            log.exit(
                "Cannot verify docker version, is your user not allowed to docker?"
            )

        safe_version = "18.09.2"
        if LooseVersion(safe_version) > LooseVersion(v):
            log.critical(
                """Your docker version is vulnerable to CVE-2019-5736

***************************************************************************************
Your docker installation (version {}) is affected by a critical vulnerability
that allows specially-crafted containers to gain administrative privileges on the host.
For details please visit: https://cve.mitre.org/cgi-bin/cvename.cgi?name=CVE-2019-5736
***************************************************************************************
To fix this issue, please update docker to version {}+
            """,
                v,
                safe_version,
            )
