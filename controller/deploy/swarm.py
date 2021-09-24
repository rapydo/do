"""
Integration with Docker swarm
"""
from typing import Dict, List, Optional, Set, Union

from glom import glom
from python_on_whales import Service
from python_on_whales.exceptions import NoSuchService, NotASwarmManager
from tabulate import tabulate

from controller import (
    COMPOSE_FILE,
    GREEN,
    RED,
    TABLE_FORMAT,
    colors,
    log,
    print_and_exit,
)
from controller.app import Application, Configuration
from controller.deploy.docker import Docker
from controller.utilities import system


class Swarm:
    def __init__(self, check_initialization: bool = True):

        self.docker = Docker().client

        if check_initialization and not self.get_token():
            print_and_exit(
                "Swarm is not initialized, please execute {command}",
                command=RED("rapydo init"),
            )

    def init(self) -> None:

        manager_address = str(
            Application.env.get("SWARM_MANAGER_ADDRESS") or system.get_local_ip()
        )

        log.info("Initializing Swarm with manager IP {}", manager_address)
        self.docker.swarm.init(advertise_address=manager_address)

    def leave(self) -> None:
        self.docker.swarm.leave(force=True)

    def get_token(self, node_type: str = "manager") -> Optional[str]:
        try:
            return str(self.docker.swarm.join_token(node_type))
        except NotASwarmManager:

            return None

    @staticmethod
    def get_service(service: str) -> str:
        return f"{Configuration.project}_{service}"

    @staticmethod
    def get_replicas(service: Service) -> int:
        if not service.spec.mode:  # pragma: no cover
            return 0

        return glom(service.spec.mode, "Replicated.Replicas", default=0)

    def stack_is_running(self, stack: str) -> bool:
        for s in self.docker.stack.list():
            if s.name == stack:
                return True
        return False

    def get_running_services(self, prefix: str) -> Set[str]:

        prefix += "_"
        containers = set()
        for service in self.docker.service.list():
            name = service.spec.name
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
            if not name.startswith(prefix):
                continue

            for task in self.docker.service.ps(name):
                status = task.status.state

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
        service_name = self.get_service(service)
        service_instance = self.docker.service.inspect(service_name)

        replicas = self.get_replicas(service_instance)
        if replicas == 0:
            scales: Dict[Union[str, Service], int] = {}
            scales[service_name] = 1
            self.docker.service.scale(scales, detach=True)
        else:
            self.docker.service.update(service_name, force=True, detach=True)

    def status(self) -> None:

        nodes: Dict[str, str] = {}
        nodes_table: List[List[str]] = []
        print("====== Nodes ======")
        for node in self.docker.node.list():
            nodes[node.id] = node.description.hostname

            state = f"{node.status.state.title()}+{node.spec.availability.title()}"
            cpu = round(node.description.resources.nano_cpus / 1000000000)
            ram = system.bytes_to_str(node.description.resources.memory_bytes)
            resources = f"{cpu} CPU {ram} RAM"

            if state == "Ready+Active":
                color_fn = GREEN
            else:
                color_fn = RED

            nodes_table.append(
                [
                    color_fn(node.spec.role.title()),
                    color_fn(state),
                    color_fn(node.description.hostname),
                    color_fn(node.status.addr),
                    color_fn(resources),
                    color_fn(",".join(node.spec.labels)),
                    color_fn(f"v{node.description.engine.engine_version}"),
                ]
            )

        print(tabulate(nodes_table, tablefmt=TABLE_FORMAT))
        services = self.docker.service.list()

        print("")

        if not services:
            log.info("No service is running")
            return

        print(colors.RESET + "====== Services ======")

        for service in services:

            service_name = service.spec.name
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

                slot = f" \\_ [{task.slot}]"
                node_name = nodes.get(task.node_id, "")
                container_name = f"{service_name}.{task.slot}.{task.id}"
                status = f"{COLOR}{task.status.state:8}{colors.RESET}"
                errors = f"err={task.status.err}" if task.status.err else ""
                labels = ",".join(task.labels)
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

    def get_container(self, service: str, slot: int) -> Optional[str]:

        service_name = self.get_service(service)
        try:
            for task in self.docker.service.ps(service_name):
                if task.slot != slot:
                    continue

                return f"{service_name}.{slot}.{task.id}"
        except NoSuchService:
            return None

        return None

    def exec_command(
        self,
        service: str,
        user: Optional[str] = None,
        command: str = None,
        disable_tty: bool = False,
        slot: int = 1,
    ) -> None:
        """
        Execute a command on a running container
        """
        log.debug("Command on {}: {}", service.lower(), command)

        container = self.get_container(service, slot)

        if not container:
            log.error("Service {} not found", service)
            return None

        exec_command = "docker exec --interactive "
        if not disable_tty:
            exec_command += "--tty "
        if user:
            exec_command += f"--user {user} "

        exec_command += f"{container} {command}"

        log.warning(
            "Due to limitations of the underlying packages, "
            "the shell command is not implemented yet"
        )

        print("")
        print("You can execute by yourself the following command:")
        print(exec_command)
        print("")

        return None

    def logs(self, service: str, follow: bool, tail: int, timestamps: bool) -> None:

        if service not in Application.data.active_services:
            print_and_exit("No such service: {}", service)

        service_name = self.get_service(service)

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

            if config.deploy.resources.reservations:
                # int() are needed because python on whales 0.25 extended type of
                # cpus and replicas to Union[float, str] according to compose-cli typing

                cpus = int(config.deploy.resources.reservations.cpus) or 0
                memory = config.deploy.resources.reservations.memory

                replicas = int(config.deploy.replicas)  # default=1

                total_cpus += replicas * cpus
                total_memory += replicas * memory

        nodes_cpus = 0.0
        nodes_memory = 0.0
        for node in self.docker.node.list():

            nodes_cpus += round(node.description.resources.nano_cpus / 1000000000)
            nodes_memory += node.description.resources.memory_bytes

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
