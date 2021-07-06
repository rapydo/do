"""
Integration with Docker swarmg
"""
import sys
from typing import Dict, List, Optional

from glom import glom
from python_on_whales import Task
from python_on_whales.utils import DockerException

from controller import COMPOSE_FILE, log
from controller.app import Application, Configuration
from controller.deploy.docker import Docker
from controller.utilities import system


class Swarm:
    def __init__(self, check_initialization: bool = True):

        self.docker = Docker().client

        if check_initialization and not self.get_token():
            Application.exit("Swarm is not initialized, please execute rapydo init")

    def init(self) -> None:
        self.docker.swarm.init()

    def leave(self) -> None:
        self.docker.swarm.leave(force=True)

    def get_token(self, node_type: str = "manager") -> Optional[str]:
        try:
            return str(self.docker.swarm.join_token(node_type))
        except DockerException:
            # log.debug(e)
            return None

    @staticmethod
    def get_service(service: str) -> str:
        return f"{Configuration.project}_{service}"

    def deploy(self) -> None:
        self.docker.stack.deploy(name=Configuration.project, compose_files=COMPOSE_FILE)

    def restart(self, service: str) -> None:
        service_name = self.get_service(service)
        self.docker.service.update(service_name, force=True, detach=True)

    def status(self) -> None:
        nodes: Dict[str, str] = {}
        print("====== Nodes ======")
        for node in self.docker.node.list():
            nodes[node.id] = node.description.hostname

            state = f"{node.status.state.title()}+{node.spec.availability.title()}"
            cpu = round(node.description.resources.nano_cpus / 1000000000)
            ram = system.bytes_to_str(node.description.resources.memory_bytes)
            resources = f"{cpu} CPU {ram} RAM"
            print(
                # node.id[0:12],
                node.spec.role.title(),
                state,
                node.description.hostname,
                node.status.addr,
                resources,
                ",".join(node.spec.labels),
                f"v{node.description.engine.engine_version}",
                sep="\t",
            )

        services = self.docker.service.list()

        print("")

        if not services:
            log.info("No service is running")
            return

        tasks: Dict[str, List[Task]] = {}

        try:
            for task in self.docker.stack.ps(Configuration.project):
                tasks.setdefault(task.service_id, [])
                tasks[task.service_id].append(task)
        except DockerException:  # pragma: no cover
            pass

        print("====== Services ======")

        for service in services:
            # replicas = service.spec.mode["Replicated"]["Replicas"]
            ports = []
            if service.endpoint.ports:
                ports = [
                    f"{p.published_port}->{p.target_port}"
                    for p in service.endpoint.ports
                ]

            image = service.spec.task_template.container_spec.image.split("@")[0]
            tasks_list = tasks.get(service.id, [])
            print(
                # service.id[0:12],
                f"{service.spec.name} ({image})",
                # f"[x {replicas}]",
                ",".join(ports),
                # ",".join(service.spec.labels),
                sep="\t",
            )

            if not tasks_list:
                print("! no task is running")

            for task in tasks_list:
                print(
                    f" \\_ [{task.slot}]",
                    # task.id[0:12],
                    nodes.get(task.node_id, ""),
                    # task.status.message,  # started
                    task.status.state,
                    task.status.timestamp.strftime("%d-%m-%Y %H:%M:%S"),
                    f"err={task.status.err}" if task.status.err else "",
                    ",".join(task.labels),
                    sep="\t",
                )

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
        except DockerException:
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
            "the shell command is not yet implemented"
        )

        print("")
        print("You can execute by yourself the following command:")
        print(exec_command)
        print("")

        return None

    def logs(
        self, services: List[str], follow: bool, tail: int, timestamps: bool
    ) -> None:

        if len(services) > 1:
            log.critical(
                "Due to limitations of the underlying packages, the logs command "
                "is only supported for single services"
            )
            sys.exit(1)

        service = services[0]

        container = self.get_container(service, 1)

        if not container:
            log.critical("No such service: {}", service)
            sys.exit(1)

        if follow:

            log.critical(
                "Due to limitations of the underlying packages, the logs command "
                "does not support the --follow flag yet"
            )
            sys.exit(1)

        print(
            self.docker.container.logs(
                container, tail=tail, details=False, timestamps=timestamps
            )
        )
        log.warning(
            "Due to limitations of the underlying packages, the logs command "
            "only prints stdout, stderr is ignored"
        )

    def check_resources(self) -> None:
        total_cpus = 0.0
        total_memory = 0.0
        for service in Application.data.active_services:
            config = Application.data.compose_config[service]

            # frontend container has no deploy options
            if "deploy" not in config:
                continue

            replicas = int(glom(config, "deploy.replicas", default=1))
            cpus = float(glom(config, "deploy.resources.reservations.cpus", default=0))
            memory = system.str_to_bytes(
                glom(config, "deploy.resources.reservations.memory", default="0")
            )

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
