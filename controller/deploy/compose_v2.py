import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union, cast

import yaml
from python_on_whales import DockerClient
from python_on_whales.components.compose.models import ComposeConfig
from python_on_whales.utils import DockerException
from tabulate import tabulate

from controller import (
    COMPOSE_ENVIRONMENT_FILE,
    COMPOSE_FILE,
    COMPOSE_FILE_VERSION,
    RED,
    REGISTRY,
    SWARM_MODE,
    TABLE_FORMAT,
    colors,
    log,
    print_and_exit,
)
from controller.app import Configuration
from controller.deploy.docker import Docker
from controller.utilities import system

Port = Union[str, int]
PortMapping = Tuple[Port, Port]
PortRangeMapping = Tuple[Port, Port, str]

# Starting from v2.0.0 _ is replaced by -
COMPOSE_SEP = "-"


class Compose:
    def __init__(self, files: List[Path]) -> None:
        self.files = files
        self.docker = DockerClient(
            compose_files=cast(List[Union[str, Path]], files),
            compose_env_file=COMPOSE_ENVIRONMENT_FILE.resolve(),
        )

    def get_config(self) -> ComposeConfig:
        # return type is Union[ComposeConfig, Dict[str, Any]] based on return_json
        return self.docker.compose.config(return_json=False)  # type: ignore

    def get_config_json(self) -> Dict[str, Any]:
        # return type is Union[ComposeConfig, Dict[str, Any]] based on return_json
        return self.docker.compose.config(return_json=True)  # type: ignore

    @staticmethod
    def create_local_path(path: Path, label: str) -> None:
        try:
            path.mkdir(parents=True)
            log.warning(
                "A {} was missing and was automatically created: {}", label, path
            )
        except PermissionError:
            uid = system.get_current_uid()
            gid = system.get_current_gid()
            command = f"sudo mkdir -p {path} && sudo chown {uid}:{gid} {path}"
            hint = f"\nSuggested command: {RED(command)}"
            print_and_exit(
                "A {} is missing and can't be automatically created: {}{}",
                label,
                path,
                hint,
            )

    def dump_config(
        self,
        services: List[str],
        set_registry: bool = True,
        v1_compatibility: bool = False,
    ) -> None:

        compose_config = self.get_config_json()

        clean_config: Dict[str, Any] = {
            "version": compose_config.get("version", COMPOSE_FILE_VERSION),
            "networks": {},
            "volumes": {},
            "services": {},
        }
        networks = set()
        volumes = set()
        binds: Set[Path] = set()

        registry = Docker.get_registry()
        # Remove unused services, networks and volumes from compose configuration
        for key, value in compose_config.get("services", {}).items():
            if key not in services:
                continue

            if SWARM_MODE and set_registry and key != REGISTRY:
                value["image"] = f"{registry}/{value['image']}"

            if "healthcheck" in value and "test" in value["healthcheck"]:
                # healtcheck commands can contain env variables double-escaped ($$)
                # When dumped to docker-compose.yml the double escape is removed
                # and when started the single escaped variable is not resolved
                # and breaks the command. Let's double all the $ to restore the
                # expected behavior and counteract the consumed $
                value["healthcheck"]["test"] = [
                    t.replace("$", "$$") for t in value["healthcheck"]["test"]
                ]

            for k, v in value.get("environment", {}).items():
                # Empty variables are converted to None...
                # and None variables are not passed to the container
                # This check can be removed when will be no longer covered
                if v is None:
                    value["environment"][k] = ""

            clean_config["services"][key] = value

            for k in value.get("networks", {}).keys():
                networks.add(k)

            for k in value.get("volumes", []):
                source = k.get("source", "")
                volume_type = k.get("type", "")
                if source and volume_type == "volume":
                    volumes.add(source.split(":")[0])
                elif source and volume_type == "bind":

                    # Remove unsupported option: 'create_host_path'
                    if v1_compatibility:
                        k.get("bind", {}).pop("create_host_path", None)

                    binds.add(Path(source.split(":")[0]))

        # Missing folders are then automatically created by the docker engine
        # the runs with root privileges and so create folders as root
        # and this can often lead to issues with permissions.

        for b in binds:
            if not b.exists():
                self.create_local_path(b, "bind folder")

        for net in networks:
            clean_config["networks"][net] = compose_config["networks"].get(net)

        for vol in volumes:
            volume_config = compose_config["volumes"].get(vol)
            if "driver_opts" in volume_config:
                device_type = volume_config["driver_opts"].get("type", "local")
                device = volume_config["driver_opts"].get("device", "")

                if device_type == "nfs" and device:
                    # starting from py39
                    # device = device.removeprefix(":")
                    if device.startswith(":"):
                        device = device[1:]
                    d = Path(device)
                    if not d.exists():
                        self.create_local_path(d, "volume path")

            clean_config["volumes"][vol] = volume_config

        with open(COMPOSE_FILE, "w") as fh:
            fh.write(yaml.dump(clean_config, default_flow_style=False))

        log.debug("Compose configuration dumped on {}", COMPOSE_FILE)

    def start_containers(
        self,
        services: List[str],
        force: bool = False,
        scales: Optional[Dict[str, int]] = None,
    ) -> None:

        if scales:
            # Based on rapydo scale implementation services is always a 1-length list
            service = services[0]
            nreplicas = scales.get(service, 0)
            services_list = f"{service}={nreplicas}"

            log.info("Scaling services: {}...", services_list)
        else:
            services_list = ", ".join(services)
            scales = {}

            log.info("Starting services ({})...", services_list)

        self.docker.compose.up(
            services=services,
            build=False,
            detach=True,
            abort_on_container_exit=False,
            force_recreate=force,
            scales=scales,
        )
        if scales:
            log.info("Services scaled: {}", services_list)
        else:
            log.info("Services started: {}", services_list)

    def create_volatile_container(
        self,
        service: str,
        command: Optional[str] = None,
        publish: Optional[List[Union[PortMapping, PortRangeMapping]]] = None,
        # used by interfaces
        detach: bool = False,
        user: Optional[str] = None,
    ) -> bool:

        compose_engine_forced = False
        if SWARM_MODE:
            # import here to prevent circular imports
            from controller.app import Application

            if not Configuration.FORCE_COMPOSE_ENGINE:
                compose_engine_forced = True
                Configuration.FORCE_COMPOSE_ENGINE = True
                # init is needed to reload the configuration to force compose engine
                Application.get_controller().controller_init()

        tty = sys.stdout.isatty()

        try:
            output = self.docker.compose.run(
                service=service,
                name=service,
                command=Docker.split_command(command),
                user=user,
                detach=detach,
                tty=tty and not detach,
                stream=not tty and not detach,
                dependencies=False,
                remove=True,
                service_ports=False,
                publish=publish or [],
                use_aliases=True,
            )

            if not detach:
                for out_line in output:  # type: ignore
                    # 'stdout' or 'stderr'
                    # Both out and err are collapsed in stdout
                    # Maybe in the future would be useful to keep them separated?
                    # stdstream = out_line[0]

                    line = out_line[1]

                    if isinstance(line, bytes):
                        line = line.decode("UTF-8")

                    print(line.strip())

            if compose_engine_forced:
                Configuration.FORCE_COMPOSE_ENGINE = False
                # init is needed to reload the configuration to undo compose engine
                Application.get_controller().controller_init()

            return True
        except DockerException as e:
            log.critical(e)
            return False

    def get_running_services(self) -> Set[str]:

        prefix = f"{Configuration.project}{COMPOSE_SEP}"
        containers = set()
        try:
            for container in self.docker.compose.ps():
                name = container.name
                if not name.startswith(prefix):
                    continue

                status = container.state.status
                if status != "running" and status != "starting" and status != "ready":
                    continue

                # to be replaced with removeprefix
                name = name[len(prefix) :]
                # Remove the _instancenumber (i.e. _1 or _n in case of scaled services)
                name = name[0 : name.index(COMPOSE_SEP)]
                containers.add(name)
            return containers
        # An exception is raised when no service is running.
        # The same happens with:
        # `docker compose ps`
        # that fails with a "not found" and it seems to be a bug of compose-cli.
        # In case it is a feature a specific exception would be helpful here
        except DockerException:
            return containers

    def get_services_status(self, prefix: str) -> Dict[str, str]:

        prefix += COMPOSE_SEP
        services_status: Dict[str, str] = dict()
        try:
            for container in self.docker.compose.ps():
                name = container.name
                if not name.startswith(prefix):
                    continue

                status = container.state.status

                # to be replaced with removeprefix
                name = name[len(prefix) :]
                # Remove the _instancenumber (i.e. _1 or _n in case of scaled services)
                name = name[0 : name.index(COMPOSE_SEP)]
                services_status[name] = status
            return services_status
        # An exception is raised when no service is running.
        # The same happens with:
        # `docker compose ps`
        # that fails with a "not found" and it seems to be a bug of compose-cli.
        # In case it is a feature a specific exception would be helpful here
        except DockerException:
            return services_status

    def status(self, services: List[str]) -> None:
        print("")

        prefix = f"{Configuration.project}{COMPOSE_SEP}"
        table: List[List[str]] = []
        for container in self.docker.compose.ps():

            name = container.name
            if not name.startswith(prefix):
                continue
            # to be replaced with removeprefix
            name = name[len(prefix) :]
            if COMPOSE_SEP in name:
                name = name[0 : name.index(COMPOSE_SEP)]

            if name not in services:
                continue

            status = container.state.status
            if status == "shutdown" or status == "complete":
                COLOR = colors.BLUE
            elif status == "running":
                COLOR = colors.GREEN
            elif status == "starting" or status == "ready":
                COLOR = colors.YELLOW
            elif status == "failed":
                COLOR = colors.RED
            else:
                COLOR = colors.RESET

            ports_list = []
            for container_port, host_port in container.network_settings.ports.items():
                if host_port:
                    container_port = container_port.split("/")[0]
                    ports_list.append(f"{container_port}->{host_port[0]['HostPort']}")

            table.append(
                [
                    container.id[0:12],
                    f"{COLOR}{container.name}{colors.RESET}",
                    status,
                    container.created.strftime("%d-%m-%Y %H:%M:%S"),
                    container.config.image,
                    ",".join(ports_list),
                ],
            )

        if not table:
            log.info("No container is running")
        else:
            print(
                tabulate(
                    table,
                    tablefmt=TABLE_FORMAT,
                    headers=["ID", "NAME", "STATUS", "CREATED", "IMAGE", "PORTS"],
                )
            )

    def logs(self, services: List[str], follow: bool = False, tail: int = 500) -> None:

        if len(services) > 1:
            timestamps = False
            log_prefix = True
        elif services[0] in "frontend":
            timestamps = True
            log_prefix = False
        else:
            timestamps = False
            log_prefix = False

        lines = self.docker.compose.logs(
            services,
            follow=follow,
            tail=str(tail),
            timestamps=timestamps,
            no_log_prefix=not log_prefix,
            stream=True,
        )
        for log_line in lines:
            # 'stdout' or 'stderr'
            # Both out and err are collapsed in stdout
            # Maybe in the future would be useful to keep them separated?
            # stdstream = log_line[0]

            line = log_line[1]

            if isinstance(line, bytes):
                line = line.decode("UTF-8")

            print(line.strip())
