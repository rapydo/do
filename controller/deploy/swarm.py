"""
Integration with Docker swarm
"""

from typing import Dict, List, Optional, Set, Union

from glom import glom
from python_on_whales import Service
from python_on_whales.exceptions import NoSuchService, NotASwarmManager

from controller import COMPOSE_FILE, RED, colors, log, print_and_exit
from controller.app import Application, Configuration
from controller.deploy.docker import Docker
from controller.utilities import system
from controller.utilities.tables import print_table


class Swarm:
    def __init__(self, docker: Docker, check_initialization: bool = True):
        self.docker_wrapper = docker
        self.docker = self.docker_wrapper.client

        if check_initialization and not self.get_token():
            print_and_exit(
                "Swarm is not initialized, please execute {command}",
                command=RED("rapydo init"),
            )

    def init(self) -> None:
        manager_address = str(
            Application.env.get("SWARM_MANAGER_ADDRESS")
            or system.get_local_ip(Configuration.production)
        )

        log.info("Initializing Swarm with manager IP {}", manager_address)
        self.docker.swarm.init(advertise_address=manager_address)

    def get_token(self, node_type: str = "manager") -> Optional[str]:
        try:
            return str(self.docker.swarm.join_token(node_type))
        except NotASwarmManager:
            return None

    @staticmethod
    def get_replicas(service: Service) -> int:
        if not service.spec.mode or "Global" in service.spec.mode:
            return 1

        return glom(service.spec.mode, "Replicated.Replicas", default=0)

    def stack_is_running(self) -> bool:
        stack = Configuration.project
        for s in self.docker.stack.list():
            if s.name == stack:
                return True
        return False

    def get_running_services(self) -> Set[str]:
        prefix = f"{Configuration.project}_"
        containers = set()
        for service in self.docker.service.list():
            name = service.spec.name
            if name is None:  # pragma: no cover
                log.warning("Got null name for {}", service)
                continue
            if not name.startswith(prefix):
                continue

            for task in self.docker.service.ps(name):
                status = task.status.state
                if status != "running" and status != "starting" and status != "ready":
                    continue

                # to be replaced with removeprefix
                name = name[len(prefix) :]
                containers.add(name)
        return containers

    def get_services_status(self, prefix: str) -> Dict[str, str]:
        prefix += "_"
        services_status: Dict[str, str] = dict()
        for service in self.docker.service.list():
            name = service.spec.name
            if name is None:  # pragma: no cover
                log.warning("Got null name for {}", service)
                continue
            if not name.startswith(prefix):
                continue

            for task in self.docker.service.ps(name):
                status = task.status.state or "N/A"

                # to be replaced with removeprefix
                name = name[len(prefix) :]
                services_status[name] = status
        return services_status

    def deploy(self) -> None:
        self.docker.stack.deploy(
            name=Configuration.project,
            compose_files=COMPOSE_FILE,
            resolve_image="always",
            prune=True,
            with_registry_auth=True,
        )

    def restart(self, service: str) -> None:
        service_name = self.docker_wrapper.get_service(service)
        service_instance = self.docker.service.inspect(service_name)

        replicas = self.get_replicas(service_instance)
        if replicas == 0:
            scales: Dict[Union[str, Service], int] = {}
            scales[service_name] = 1
            self.docker.service.scale(scales, detach=True)
        else:
            self.docker.service.update(service_name, force=True, detach=True)

    def status(self, services: List[str]) -> None:
        nodes: Dict[str, str] = {}
        nodes_table: List[List[str]] = []
        headers = ["Role", "State", "Name", "IP", "CPUs", "RAM", "LABELS", "Version"]
        for node in self.docker.node.list():
            node_hostname = node.description.hostname or "N/A"
            node_addr = node.status.addr or "N/A"
            nodes[node.id] = node_hostname

            state = cpu = ram = ""
            if node.status.state and node.spec.availability:
                state = f"{node.status.state.title()}+{node.spec.availability.title()}"
            if node.description.resources and node.description.resources.nano_cpus:
                cpu = str(round(node.description.resources.nano_cpus / 1000000000))
            if node.description.resources and node.description.resources.memory_bytes:
                ram = system.bytes_to_str(node.description.resources.memory_bytes)

            if state == "Ready+Active":
                p = "[bold green]"
                s = "[/bold green]"
            else:
                p = "[bold red]"
                s = "[/bold red]"

            node_role = "N/A"
            if node.spec.role:
                node_role = node.spec.role.title()

            node_labels = ""
            if node.spec.labels:
                node_labels = ",".join(node.spec.labels)

            engine_version = "N/A"
            if node.description.engine and node.description.engine.engine_version:
                engine_version = f"v{node.description.engine.engine_version}"

            nodes_table.append(
                [
                    p + (node_role) + s,
                    p + (state) + s,
                    p + (node_hostname) + s,
                    p + (node_addr) + s,
                    p + (cpu) + s,
                    p + (ram) + s,
                    p + (node_labels) + s,
                    p + (engine_version) + s,
                ]
            )

        print_table(headers, nodes_table, table_title="Cluster status")
        stack_services = self.docker.service.list()

        print("")

        if not stack_services:
            log.info("No service is running")
            return

        prefix = f"{Configuration.project}_"
        for service in stack_services:
            service_name = service.spec.name or "N/A"

            tmp_service_name = service_name
            if tmp_service_name.startswith(prefix):
                # to be replaced with removeprefix
                tmp_service_name = tmp_service_name[len(prefix) :]
            if tmp_service_name not in services:
                continue

            print(f"{colors.RESET}Inspecting {service_name}...", end="\r")

            tasks_lines: List[str] = []

            running_tasks = 0
            for task in self.docker.service.ps(service_name):
                if task.status.state == "shutdown" or task.status.state == "complete":
                    COLOR = colors.BLUE
                elif task.status.state == "running":
                    COLOR = colors.GREEN
                    running_tasks += 1
                elif task.status.state == "starting" or task.status.state == "ready":
                    COLOR = colors.YELLOW
                elif task.status.state == "failed":
                    COLOR = colors.RED
                else:
                    COLOR = colors.RESET

                if task.slot:
                    slot = f" \\_ [{task.slot}]"
                    container_name = f"{service_name}.{task.slot}.{task.id}"
                else:
                    slot = " \\_ [H]"
                    container_name = f"{service_name}.{task.node_id}.{task.id}"

                node_name = nodes.get(task.node_id, "")
                status = f"{COLOR}{task.status.state:8}{colors.RESET}"
                errors = f"err={task.status.err}" if task.status.err else ""
                labels = ",".join(task.labels)
                ts = "N/A"
                if task.status.timestamp:
                    ts = task.status.timestamp.strftime("%d-%m-%Y %H:%M:%S")

                tasks_lines.append(
                    "\t".join(
                        (
                            slot,
                            status,
                            ts,
                            node_name,
                            container_name,
                            errors,
                            labels,
                        )
                    )
                )

            # Very ugly, to reset the color with \r
            print("                                                         ", end="\r")

            replicas = self.get_replicas(service)

            if replicas == 0:
                COLOR = colors.YELLOW
            elif replicas != running_tasks:
                COLOR = colors.RED
            else:
                COLOR = colors.GREEN

            if service.endpoint.ports:
                ports_list = [
                    f"{p.published_port}->{p.target_port}"
                    for p in service.endpoint.ports
                ]
            else:
                ports_list = []

            image = "N/A"
            if (
                service.spec.task_template
                and service.spec.task_template.container_spec
                and service.spec.task_template.container_spec.image
            ):
                image = service.spec.task_template.container_spec.image.split("@")[0]
            ports = ",".join(ports_list)
            print(
                f"{COLOR}{service_name:23}{colors.RESET} [{replicas}] {image}\t{ports}"
            )

            for line in tasks_lines:
                print(line)

            print("")

    def remove(self) -> None:
        self.docker.stack.remove(Configuration.project)

    def logs(self, service: str, follow: bool, tail: int, timestamps: bool) -> None:
        if service not in Application.data.active_services:
            print_and_exit("No such service: {}", service)

        service_name = self.docker_wrapper.get_service(service)

        try:
            # lines: Iterable[Tuple[str, bytes]] due to stream=True
            # without stream=True the type would be :str
            lines = self.docker.service.logs(
                service_name,
                task_ids=False,
                resolve=True,
                truncate=True,
                # since=None,
                tail=tail,
                details=False,
                timestamps=timestamps,
                follow=follow,
                stream=True,
            )

        except NoSuchService:
            print_and_exit(
                "No such service {}, is the stack still starting up?", service
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

    def check_resources(self) -> None:
        total_cpus = 0.0
        total_memory = 0.0
        for service in Application.data.active_services:
            config = Application.data.compose_config[service]

            # frontend container has no deploy options
            if not config.deploy:
                continue

            if config.deploy.resources and config.deploy.resources.reservations:
                # int() are needed because python on whales 0.25 extended type of
                # cpus and replicas to Union[float, str] according to compose-cli typing

                cpus = int(config.deploy.resources.reservations.cpus or 0)
                memory = config.deploy.resources.reservations.memory or 0

                # the proxy container is now defined as global and without any replicas
                # => replicas is None => defaulted to 1
                replicas = int(config.deploy.replicas or 1)

                total_cpus += replicas * cpus
                total_memory += replicas * memory

        nodes_cpus = 0.0
        nodes_memory = 0.0
        for node in self.docker.node.list():
            if node.description.resources:
                nodes_cpus += round(
                    (node.description.resources.nano_cpus or 0) / 1000000000
                )
                nodes_memory += node.description.resources.memory_bytes or 0

        if total_cpus > nodes_cpus:
            log.critical(
                "Your deployment requires {} cpus but your nodes only have {}",
                total_cpus,
                nodes_cpus,
            )

        if total_memory > nodes_memory:
            log.critical(
                "Your deployment requires {} of RAM but your nodes only have {}",
                system.bytes_to_str(total_memory),
                system.bytes_to_str(nodes_memory),
            )
