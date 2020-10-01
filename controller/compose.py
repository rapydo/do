"""
Integration with Docker compose

# NOTE: A way to possibly silence compose output:
https://stackoverflow.com/questions/2828953/silence-the-stdout-of-a-function-in-python-without-trashing-sys-stdout-and-resto
"""
import os
import re
import shlex
from contextlib import redirect_stdout
from io import StringIO

from compose import errors as cerrors
from compose.cli import errors as clierrors
from compose.cli.command import (
    get_config_from_options,
    get_project_name,
    project_from_options,
)
from compose.cli.main import TopLevelCommand
from compose.network import NetworkConfigChangedError
from compose.project import NoSuchService, ProjectError
from compose.service import BuildError

from controller import log


class Compose:
    def __init__(self, files):
        super().__init__()

        self.files = files

        self.options = {"--file": self.files}

        self.project_name = get_project_name(os.curdir)

        os.environ["COMPOSE_HTTP_TIMEOUT"] = "180"

        log.verbose("Client compose {}: {}", self.project_name, files)

    def config(self):
        compose_output_tuple = get_config_from_options(".", self.options)
        # NOTE: for compatibility with docker-compose > 1.13
        # services is always the second element
        return compose_output_tuple[1]

    def command(self, command, options):

        compose_handler = TopLevelCommand(project_from_options(os.curdir, self.options))
        method = getattr(compose_handler, command)

        if options.get("SERVICE", None) is None:
            options["SERVICE"] = []

        log.debug("docker-compose command: '{}'", command)

        out = None
        # sometimes this import stucks... importing here to avoid unnecessary waits
        from docker.errors import APIError

        try:
            out = method(options=options)
        except SystemExit as e:
            # System exit is always received, also in case of normal execution
            if e.code > 0:
                log.exit("Compose received: system.exit({})", e.code, error_code=e.code)

            log.verbose("Executed compose {} w/{}", command, options)
        except (clierrors.UserError, cerrors.OperationFailedError, BuildError) as e:
            log.exit("Failed command execution:\n{}", e)
        except (clierrors.ConnectionError, APIError) as e:  # pragma: no cover
            log.exit("Failed docker container:\n{}", e)
        except (ProjectError, NoSuchService) as e:
            log.exit(e)
        else:
            log.verbose("Executed compose {} w/{}", command, options)

        return out

    @staticmethod
    def split_command(command):
        """
        Split a command into command + args_array
        """
        if command is None:
            return (None, [])

        # pieces = command.split()
        pieces = shlex.split(command)
        try:
            shell_command = pieces[0]
            shell_args = pieces[1:]
            return (shell_command, shell_args)
        except IndexError:
            # no command, use default
            return (None, [])

    def start_containers(
        self,
        services,
        # used by backup
        detach=True,
        # used by scale
        scale=None,
        # used by scale
        skip_dependencies=False,
        # used by start
        force_recreate=False,
    ):
        """
        Start containers (docker-compose up)
        """

        if scale is None:
            scale = {}

        options = {
            "SERVICE": services,
            "--no-deps": skip_dependencies,
            "--detach": detach,
            "--build": None,
            "--no-color": False,
            "--remove-orphans": False,
            "--abort-on-container-exit": False,
            "--no-recreate": False,
            "--force-recreate": force_recreate,
            "--always-recreate-deps": False,
            "--no-build": False,
            "--scale": scale,
        }

        try:
            return self.command("up", options)
        except NetworkConfigChangedError as e:  # pragma: no cover
            log.exit(
                "{}.\n{} ({})",
                e,
                "Remove previously created networks and try again",
                "you can use rapydo remove --networks or docker system prune",
            )

    def create_volatile_container(
        self, service, command=None, publish=None, detach=False, user=None
    ):
        """
        Execute a command on a not container
        """

        if publish is None:
            publish = []

        if len(publish) <= 0:
            service_post = True
        else:
            service_post = False

        shell_command, shell_args = self.split_command(command)

        options = {
            "SERVICE": service,
            "--publish": publish,
            "--service-ports": service_post,
            "COMMAND": shell_command,
            "ARGS": shell_args,
            "-e": [],
            "--volume": [],
            "--rm": True,
            "--no-deps": True,
            "--name": None,
            "--user": user,
            "--workdir": None,
            "--entrypoint": None,
            "--detach": detach,
            "--use-aliases": False,  # introduced with compose 1.21
            "-T": False,
            "--label": None,
        }

        return self.command("run", options)

    def exec_command(
        self, service, user=None, command=None, disable_tty=False, detach=False
    ):
        """
        Execute a command on a running container
        """
        shell_command, shell_args = self.split_command(command)
        options = {
            "SERVICE": service,
            "COMMAND": shell_command,
            "ARGS": shell_args,
            "--index": "1",
            "--user": user,
            "-T": disable_tty,
            "--env": None,
            "--workdir": None,
            # '-d': False,
            "--detach": detach,
            "--privileged": False,
        }
        if shell_command is not None:
            log.debug(
                "Command on {}: {} {}",
                service.lower(),
                shell_command,
                " ".join(shell_args),
            )
        return self.command("exec_command", options)

    def get_containers_status(self, prefix):
        with StringIO() as buf, redirect_stdout(buf):
            self.command("ps", {"--quiet": False, "--services": False, "--all": False})
            output = buf.getvalue().split("\n")

            containers = {}
            for row in output:
                if row == "":
                    continue
                if row.startswith(" "):
                    continue
                if row.startswith("---"):
                    continue
                # row is:
                # Name   Command   State   Ports
                # Split on two or more spaces
                row = re.split(r"\s\s+", row)
                status = row[2]
                row = row[0]
                if row == "Name":
                    continue
                # Removed the prefix (i.e. project name)
                row = row[1 + len(prefix) :]
                # Remove the _instancenumber (i.e. _1 or _n in case of scaled services)
                row = row[0 : row.index("_")]

                containers[row] = status

            return containers

    def get_running_containers(self, prefix):
        containers_status = self.get_containers_status(prefix)
        containers = set()
        for name, status in containers_status.items():
            if status != "Up":
                continue
            containers.add(name)
        return containers
