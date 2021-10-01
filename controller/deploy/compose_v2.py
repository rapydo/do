import shlex
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
    RED,
    REGISTRY,
    SWARM_MODE,
    TABLE_FORMAT,
    colors,
    log,
    print_and_exit,
)
from controller.deploy.docker import Docker
from controller.utilities import system

Port = Union[str, int]
PortMapping = Tuple[Port, Port]
PortRangeMapping = Tuple[Port, Port, str]


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
            "version": compose_config.get("version", "3.8"),
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

    @staticmethod
    def split_command(command: Optional[str]) -> List[str]:
        # Needed because:
        # Passing None for 's' to shlex.split() is deprecated
        if command is None:
            return []

        return shlex.split(command)

    def create_volatile_container(
        self,
        service: str,
        command: Optional[str] = None,
        publish: Optional[List[Union[PortMapping, PortRangeMapping]]] = None,
        # used by interfaces
        detach: bool = False,
        user: Optional[str] = None,
    ) -> None:

        # equivalent to command is not None and len(command) > 0
        # or not(not command) ...
        if command:
            tty = True
        else:
            tty = False

        out = self.docker.compose.run(
            service=service,
            name=service,
            command=self.split_command(command),
            user=user,
            detach=detach,
            # Attach a tty if a command is specified
            # but interactive commands is not working
            tty=tty,
            dependencies=False,
            # Error in python on whales 0.27 to be restored once fixed
            # remove=True,
            # Enable services ports only if publish is empty
            service_ports=not publish,
            publish=publish or [],
            use_aliases=True,
        )

        if not detach:
            print(out)

    def get_running_services(self, prefix: str) -> Set[str]:

        prefix += "_"
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
                name = name[0 : name.index("_")]
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

        prefix += "_"
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
                name = name[0 : name.index("_")]
                services_status[name] = status
            return services_status
        # An exception is raised when no service is running.
        # The same happens with:
        # `docker compose ps`
        # that fails with a "not found" and it seems to be a bug of compose-cli.
        # In case it is a feature a specific exception would be helpful here
        except DockerException:
            return services_status

    def status(self) -> None:
        print("")

        table: List[List[str]] = []
        for container in self.docker.compose.ps():

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
