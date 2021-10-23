"""
Integration with Docker compose

# NOTE: A way to possibly silence compose output:
https://stackoverflow.com/questions/2828953/silence-the-stdout-of-a-function-in-python-without-trashing-sys-stdout-and-resto
"""
import os
import shlex
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from compose import errors as cerrors
from compose.cli import errors as clierrors
from compose.cli.command import get_project_name, project_from_options
from compose.cli.main import TopLevelCommand
from compose.cli.signals import ShutdownException
from compose.network import NetworkConfigChangedError
from compose.project import NoSuchService, ProjectError
from compose.service import BuildError

from controller import COMPOSE_ENVIRONMENT_FILE, RED, log, print_and_exit

COMPOSE_SEP = "_"


class Compose:
    def __init__(self, files: List[Path]) -> None:
        self.files = files
        self.options = {
            "--file": self.files,
            # Resolve to absolute path
            "--env-file": str(COMPOSE_ENVIRONMENT_FILE.resolve()),
        }

        self.project_name = get_project_name(os.curdir)

        os.environ["COMPOSE_HTTP_TIMEOUT"] = "180"
        os.environ["DOCKER_BUILDKIT"] = "1"

        log.debug("Client compose {}: {}", self.project_name, files)

    def command(self, command: str, options: Dict[str, Any]) -> None:

        compose_handler = TopLevelCommand(project_from_options(os.curdir, self.options))
        method = getattr(compose_handler, command)

        if options.get("SERVICE", None) is None:
            options["SERVICE"] = []

        log.debug("docker-compose command: '{}'", command)

        # sometimes this import stucks... importing here to avoid unnecessary waits
        from docker.errors import APIError  # type: ignore

        try:
            method(options=options)
        except SystemExit as e:
            # System exit is always received, also in case of normal execution
            if e.code > 0:
                log.critical("Compose received: system.exit({})", e.code)
                sys.exit(e.code)

        except (clierrors.UserError, cerrors.OperationFailedError, BuildError) as e:
            print_and_exit("Failed command execution:\n{}", e)
        except (clierrors.ConnectionError, APIError) as e:  # pragma: no cover
            print_and_exit("Failed docker container:\n{}", e)
        except ShutdownException as e:  # pragma: no cover
            print_and_exit("ShutdownException {}", e)
        except (ProjectError, NoSuchService) as e:
            print_and_exit(e)

    @staticmethod
    def split_command(command: Optional[str]) -> Tuple[Optional[str], List[str]]:
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
        services: List[str],
        # used by scale
        scale: Optional[List[str]] = None,
        # used by scale
        skip_dependencies: bool = False,
    ) -> None:
        """
        Start containers (docker-compose up)
        """

        if scale is None:
            scale = []
            # scale = {}

        options = {
            "SERVICE": services,
            "--no-deps": skip_dependencies,
            "--detach": True,
            "--build": None,
            "--no-color": False,
            "--remove-orphans": False,
            "--abort-on-container-exit": False,
            "--no-recreate": False,
            "--force-recreate": False,
            "--always-recreate-deps": False,
            "--no-build": False,
            "--scale": scale,
        }

        try:
            self.command("up", options)
        except NetworkConfigChangedError as e:  # pragma: no cover
            print_and_exit(
                "{}.\n{} ({})",
                e,
                "Remove previously created networks and try again",
                "you can use {command1} or {command2}",
                command1=RED("rapydo remove"),
                command2=RED("docker system prune"),
            )

    def create_volatile_container(
        self,
        service: str,
        command: Optional[str] = None,
        publish: Optional[List[str]] = None,
        # used by interfaces
        detach: bool = False,
        user: Optional[str] = None,
    ) -> None:
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
            "--name": service,
            "--user": user,
            "--workdir": None,
            "--entrypoint": None,
            "--detach": detach,
            "--use-aliases": False,  # introduced with compose 1.21
            "-T": False,
            "--label": None,
        }

        self.command("run", options)
