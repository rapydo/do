"""
Integration with Docker compose

# NOTE: A way to possibly silence compose output:
https://stackoverflow.com/questions/2828953/silence-the-stdout-of-a-function-in-python-without-trashing-sys-stdout-and-resto
"""
import os
import re
import shlex
import sys
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, cast

import yaml
from compose import errors as cerrors
from compose.cli import errors as clierrors
from compose.cli.command import (
    get_config_from_options,
    get_project_name,
    project_from_options,
)
from compose.cli.main import TopLevelCommand
from compose.cli.signals import ShutdownException
from compose.config.serialize import serialize_config
from compose.network import NetworkConfigChangedError
from compose.project import NoSuchService, ProjectError
from compose.service import BuildError

from controller import COMPOSE_ENVIRONMENT_FILE, log, print_and_exit


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

    def config(self, relative_paths: bool = False) -> Dict[str, Any]:
        compose_config = get_config_from_options(".", self.options)
        yaml_string = serialize_config(compose_config, None, True)

        if relative_paths:
            yaml_string = yaml_string.replace(os.getcwd(), ".")

        return cast(Dict[str, Any], yaml.safe_load(yaml_string))

    @staticmethod
    def dump_config(
        compose_config: Dict[str, Any], path: Path, active_services: List[str]
    ) -> None:

        clean_config: Dict[str, Any] = {
            "version": compose_config.get("version", "3.8"),
            "networks": {},
            "volumes": {},
            "services": {},
        }
        networks = set()
        volumes = set()
        # Remove unused services, networks and volumes from compose configuration
        for key, value in compose_config.get("services", {}).items():
            if key not in active_services:
                continue
            clean_config["services"][key] = value

            for k in value.get("networks", {}).keys():
                networks.add(k)

            for k in value.get("volumes", []):
                if k.startswith("/") or k.startswith("./"):
                    continue
                volumes.add(k.split(":")[0])

        for net in networks:
            clean_config["networks"][net] = compose_config["networks"].get(net)

        for vol in volumes:
            clean_config["volumes"][vol] = compose_config["volumes"].get(vol)

        with open(path, "w") as fh:
            fh.write(yaml.dump(clean_config, default_flow_style=False))

    def command(self, command: str, options: Dict[str, Any]) -> None:

        compose_handler = TopLevelCommand(project_from_options(os.curdir, self.options))
        method = getattr(compose_handler, command)

        if options.get("SERVICE", None) is None:
            options["SERVICE"] = []

        log.debug("docker-compose command: '{}'", command)

        # sometimes this import stucks... importing here to avoid unnecessary waits
        from docker.errors import APIError

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
        # used by start
        force_recreate: bool = False,
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
            "--force-recreate": force_recreate,
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
                "you can use rapydo remove --networks or docker system prune",
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

        self.command("run", options)

    def exec_command(
        self,
        service: str,
        user: Optional[str] = None,
        command: str = None,
        disable_tty: bool = False,
    ) -> None:
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
            "--detach": False,
            "--privileged": False,
        }
        if shell_command is not None:
            log.debug(
                "Command on {}: {} {}",
                service.lower(),
                shell_command,
                " ".join(shell_args),
            )
        self.command("exec_command", options)

    def get_containers_status(self, prefix: str) -> Dict[str, str]:
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
                row_tokens = re.split(r"\s\s+", row)

                if row_tokens[0] == "Name":
                    continue

                status = row_tokens[2]
                name = row_tokens[0]

                # Removed the prefix (i.e. project name)
                name = name[1 + len(prefix) :]
                # Remove the _instancenumber (i.e. _1 or _n in case of scaled services)
                name = name[0 : name.index("_")]

                containers[name] = status

            return containers

    def get_running_containers(self, prefix: str) -> Set[str]:
        containers_status = self.get_containers_status(prefix)
        containers = set()
        for name, status in containers_status.items():
            if not status.startswith("Up"):
                continue

            if status == "Up (unhealthy)":  # pragma: no cover
                log.error("Status of {} container is unhealthy", name)

            containers.add(name)
        return containers
