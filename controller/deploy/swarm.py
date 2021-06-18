"""
Integration with Docker swarmg
"""

from typing import Any, Dict, List, Optional

from glom import glom
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

    def deploy(self) -> None:
        self.docker.stack.deploy(name=Configuration.project, compose_files=COMPOSE_FILE)

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

        # This Any should be python_on_whales.Task but:
        # Type of variable becomes Any due to an unfollowed import
        tasks: Dict[str, List[Any]] = {}

        try:
            for task in self.docker.stack.ps(Configuration.project):
                tasks.setdefault(task.service_id, [])
                tasks[task.service_id].append(task)
        except DockerException:  # pragma: no cover
            pass

        print("====== Services ======")

        for service in services:
            ports = []
            if service.endpoint.ports:
                ports = [
                    f"{p.published_port}->{p.target_port}"
                    for p in service.endpoint.ports
                ]

            print("")
            image = service.spec.task_template.container_spec.image.split("@")[0]
            print(
                # service.id[0:12],
                f"{service.spec.name} ({image})",
                ",".join(ports),
                # ",".join(service.spec.labels),
                sep="\t",
            )

            tasks_list = tasks.get(service.id, [])

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
                    f"err={task.status.err}",
                    ",".join(task.labels),
                    sep="\t",
                )

    def scale(self, service: str, nreplicas: int) -> None:
        self.docker.service.scale(
            {f"{Configuration.project}_{service}": nreplicas}, detach=False
        )

    def remove(self) -> None:
        self.docker.stack.remove(Configuration.project)

    def get_container(self, service: str, slot: int) -> Optional[str]:

        service_id: Optional[str] = None
        services = self.docker.service.list()
        for s in services:
            if s.spec.name == f"{Configuration.project}_{service}":
                service_id = s.id
                break

        if not service_id:
            return None

        for task in self.docker.stack.ps(Configuration.project):
            if task.service_id != service_id:
                continue
            if task.slot != slot:
                continue

            return f"{Configuration.project}_{service}.{slot}.{task.id}"

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

        log.warning(
            "Due to limitations of the underlying packages, "
            "the logs command is not yet implemented"
        )

        print("")
        print("You can execute by yourself the following command(s):")

        for service in services:
            container = self.get_container(service, 1)

            if not container:
                log.error("Service {} not found", service)
                continue

            logs_command = f"docker logs --tail {tail} "
            if follow:
                logs_command += "--follow "
            if timestamps:
                logs_command += "--timestamps "

            logs_command += f"{container}"

            print(logs_command)
            print("")

        return None

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
