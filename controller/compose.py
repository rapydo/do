"""
Integration with Docker compose

# NOTE: A way to possibly silence compose output:
https://stackoverflow.com/questions/2828953/silence-the-stdout-of-a-function-in-python-without-trashing-sys-stdout-and-resto
"""
import os
import shlex

import compose.cli.errors as clierrors
import compose.config.errors as conferrors
import compose.errors as cerrors
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

    # def __init__(self, files, options={}):
    # def __init__(self, files, net=None):
    def __init__(self, files):
        super().__init__()

        self.files = files
        # options.update({'--file': self.files})
        self.options = {"--file": self.files}
        # if net is not None:
        #     self.options['--net'] = net

        self.project_dir = os.curdir
        self.project_name = get_project_name(self.project_dir)
        log.verbose("Client compose {}: {}", self.project_name, files)

    def config(self):
        compose_output_tuple = get_config_from_options(".", self.options)
        # NOTE: for compatibility with docker-compose > 1.13
        # services is always the second element
        return compose_output_tuple[1]

    def command(self, command, options):

        compose_handler = TopLevelCommand(
            project_from_options(self.project_dir, self.options)
        )
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
            # NOTE: we check the status here.
            # System exit is received also when a normal command finished.
            if e.code == 0:
                log.verbose("Executed compose {} w/{}", command, options)
            else:
                log.exit("Compose received: system.exit({})", e.code, error_code=e.code)
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
        detach=True,
        scale=None,
        skip_dependencies=False,
        abort_on_container_exit=False,
        no_recreate=False,
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
            "--abort-on-container-exit": abort_on_container_exit,
            "--no-recreate": no_recreate,
            "--force-recreate": False,
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

    def exec_command(self, service, user=None, command=None, disable_tty=False):
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
            "--detach": False,
            "--privileged": False,
        }
        if shell_command is not None:
            log.debug("Command: {}({}+{})", service.lower(), shell_command, shell_args)
        try:
            return self.command("exec_command", options)
        except NoSuchService:
            log.exit("Cannot find a running container called {}", service)
