import re
import shlex
import sys
from functools import lru_cache
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set, Tuple, Union, cast

from python_on_whales import DockerClient
from python_on_whales.exceptions import NoSuchContainer, NoSuchService
from python_on_whales.utils import DockerException

from controller import COMPOSE_ENVIRONMENT_FILE, log
from controller.app import Application, Configuration
from controller.utilities import system

MAIN_NODE = "manager"
# Starting from v2.0.0 _ is replaced by -
COMPOSE_SEP = "-"


class Docker:
    def __init__(
        self, compose_files: Optional[List[Path]] = None, verify_swarm: bool = True
    ) -> None:

        if not compose_files:
            # Not all commands initialize Application.data
            # e.g. init does not
            if hasattr(Application, "data"):
                compose_files = Application.data.files

        if compose_files:
            self.client = DockerClient(
                compose_files=cast(List[Union[str, Path]], compose_files),
                compose_env_file=COMPOSE_ENVIRONMENT_FILE.resolve(),
                host=self.get_engine(Configuration.remote_engine),
            )

        else:
            self.client = DockerClient(
                host=self.get_engine(Configuration.remote_engine),
            )

        # temporary added here to prevent circular imports, to be moved upside
        from controller.deploy.registry import Registry

        self.registry = Registry(docker=self)

        # temporary added here to prevent circular imports, to be moved upside
        from controller.deploy.swarm import Swarm

        self.swarm = Swarm(
            docker=self, check_initialization=verify_swarm and Configuration.swarm_mode
        )

        if compose_files:
            # temporary added here to prevent circular imports, to be moved upside
            from controller.deploy.compose_v2 import Compose

            self.compose = Compose(docker=self)

    @lru_cache
    def connect_engine(self, node_id: str) -> DockerClient:
        """Convert a node_id to a docker client connected to the engine hostname"""

        if not node_id or node_id == MAIN_NODE or not Configuration.swarm_mode:
            return self.client

        node = self.client.node.inspect(node_id)

        # Always use the default client if executing on localhost
        if node.status.addr == system.get_local_ip(production=False):
            return self.client

        # manager address should be localhost in dev mode, something else in prod mode
        manager_address = str(
            Application.env.get("SWARM_MANAGER_ADDRESS")
            or system.get_local_ip(Configuration.production)
        )

        if node.status.addr == manager_address:
            return self.client

        return DockerClient(host=self.get_engine(node.status.addr))

    @classmethod
    def get_engine(cls, engine: Optional[str]) -> Optional[str]:

        if not engine:
            return None

        if engine == MAIN_NODE:
            return None

        if "@" not in engine:
            user = system.get_username(system.get_current_uid())
            engine = f"{user}@{engine}"

        return f"ssh://{engine}"

    @classmethod
    def get_service(cls, service: str) -> str:
        if Configuration.swarm_mode:
            return f"{Configuration.project}_{service}"
        return f"{Configuration.project}{COMPOSE_SEP}{service}"

    def get_services_status(self, prefix: str) -> Dict[str, str]:
        if Configuration.swarm_mode:
            return self.swarm.get_services_status(prefix)
        else:
            return self.compose.get_services_status(prefix)

    def get_running_services(self) -> Set[str]:
        if Configuration.swarm_mode:
            return self.swarm.get_running_services()
        else:
            return self.compose.get_running_services()

    def get_containers(self, service: str) -> Dict[int, Tuple[str, str]]:

        containers: Dict[int, Tuple[str, str]] = {}
        service_name = self.get_service(service)

        if Configuration.swarm_mode:
            try:
                for task in self.client.service.ps(service_name):
                    if task.status.state not in ("running", "starting", "ready"):
                        continue
                    # this is the case of services set with `mode: global`
                    if task.slot is None:
                        containers.setdefault(
                            0,
                            (
                                f"{service_name}.{task.node_id}.{task.id}",
                                task.node_id,
                            ),
                        )
                        break

                    containers.setdefault(
                        task.slot,
                        (
                            f"{service_name}.{task.slot}.{task.id}",
                            task.node_id,
                        ),
                    )
            except (NoSuchService, NoSuchContainer):
                return containers
        else:
            prefix = f"{service_name}{COMPOSE_SEP}"
            for c in self.client.container.list():
                if not c.name.startswith(prefix):
                    continue
                # from py39 use removeprefix
                # slot = c.name.removeprefix(prefix)
                slot = int(c.name[len(prefix) :])
                containers.setdefault(slot, (c.name, MAIN_NODE))
        return containers

    def get_container_name(self, service_name: str, slot: int = 1) -> str:
        return f"{service_name}{COMPOSE_SEP}{slot}"

    def get_container(self, service: str, slot: int = 1) -> Optional[Tuple[str, str]]:

        if Configuration.swarm_mode:
            tasks = self.get_containers(service)
            # the 0 index is found in case of containers in global mode, like the proxy
            return tasks.get(slot) or tasks.get(0)

        service_name = self.get_service(service)
        c = self.get_container_name(service_name, slot=slot)
        log.debug("Container name: {}", c)
        # Can't use container.exists because a check on the status is needed
        try:
            container = self.client.container.inspect(c)
            status = container.state.status
            if status not in ("running", "starting", "ready"):
                log.warning(
                    "Found a container for {}, but status is {}", service, status
                )
                return None
            return (c, MAIN_NODE)
        except NoSuchContainer:
            return None

    @staticmethod
    def split_command(command: Optional[str]) -> List[str]:
        # Needed because:
        # Passing None for 's' to shlex.split() is deprecated
        if command is None:
            return []

        return shlex.split(command)

    def exec_command(
        self,
        # Tuple[str, str] == return of get_container
        # Dict[int, Tuple[str, str]] == return of get_containers
        containers: Union[str, Tuple[str, str], Dict[int, Tuple[str, str]]],
        user: Optional[str],
        command: str = None,
        # this basically force tty=False
        force_output_return: bool = False,
    ) -> Optional[Union[str, Iterable[Tuple[str, bytes]]]]:

        if isinstance(containers, str):
            containers = (
                containers,
                MAIN_NODE,
            )

        if isinstance(containers, tuple):
            containers_list = [containers]
        else:
            containers_list = list(sorted(containers.values()))

        broadcast = len(containers_list) > 1

        # Important security note: never log the command command because it can
        # contain sensitive data, for example when used from change password command
        tty = not force_output_return and sys.stdout.isatty()
        for container in containers_list:

            try:
                client = self.connect_engine(container[1])
                if client.client_config.host:
                    log.info(
                        "Executing command on {}:{}",
                        client.client_config.host,
                        container[0],
                    )
                elif broadcast:
                    log.info("Executing command on {}", container[0])

                output = client.container.execute(
                    container[0],
                    user=user,
                    command=self.split_command(command),
                    interactive=tty,
                    tty=tty,
                    stream=not tty,
                    detach=False,
                )

                if force_output_return:
                    return output
                # When tty is enabled the output is empty because the terminal is
                # directly connected to the container I/O bypassing python
                # Important: when the tty is disabled exceptions are not raised by
                # container.execute but by the loop => keep both in the try/except
                if output:
                    for out_line in output:
                        # 'stdout' or 'stderr'
                        # Both out and err are collapsed in stdout
                        # Maybe in the future would be useful to keep them separated?
                        # stdstream = out_line[0]

                        line = out_line[1]

                        if isinstance(line, bytes):
                            line = line.decode("UTF-8")

                        print(line.strip())

            except DockerException as e:

                m = re.search(r"It returned with code (\d+)\n", str(e))
                if not m:
                    log.debug("Catched exception does not contains any valid exit code")
                    raise e

                exit_code = m.group(1)

                # Based on docker exit codes https://github.com/moby/moby/pull/14012
                # which follows standard chroot exit codes
                # https://tldp.org/LDP/abs/html/exitcodes.html
                if exit_code == "126":
                    # rapydo shell backend "invalid"
                    motivation = "command cannot be invoked"
                elif exit_code == "127":
                    # rapydo shell backend "bash invalid"
                    motivation = "command not found"
                elif exit_code == "130":  # pragma: no cover
                    # container ctrl+c will executing (i.e. rapydo shell backend)
                    motivation = "Control-C"
                elif exit_code == "137":  # pragma: no cover
                    # container restart will executing (i.e. rapydo shell backend)
                    motivation = "SIGKILL"
                elif exit_code == "143":  # pragma: no cover
                    motivation = "SIGTERM"
                else:  # pragma: no cover
                    motivation = "an unknown cause"
                    exit_code = "1"
                    log.debug(str(e))

                log.error(
                    "The command execution was terminated by {}. Exit code is {}",
                    motivation,
                    exit_code,
                )
                sys.exit(int(exit_code))

        return None

    def status(self, services: List[str]) -> None:
        if Configuration.swarm_mode:
            return self.swarm.status(services)
        else:
            return self.compose.status(services)

    def remove(self, service: str) -> None:
        if Configuration.swarm_mode:
            service_name = Docker.get_service(service)
            self.client.service.scale({service_name: 0}, detach=False)
        else:
            self.client.compose.rm([service], stop=True, volumes=False)

    def start(self, service: str) -> None:
        if Configuration.swarm_mode:
            self.swarm.deploy()
        else:
            self.compose.start_containers([service])
