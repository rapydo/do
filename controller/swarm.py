"""
Integration with Docker swarmg
"""

from typing import Dict, List, Optional

from python_on_whales import Task, docker
from python_on_whales.utils import DockerException

from controller import COMPOSE_FILE, log
from controller.app import Configuration
from controller.utilities import system


class Swarm:
    def __init__(self):
        pass

    @staticmethod
    def init() -> None:
        docker.swarm.init()

    @staticmethod
    def leave() -> None:
        docker.swarm.leave(force=True)

    @staticmethod
    def get_token(node_type: str = "manager") -> Optional[str]:
        try:
            return str(docker.swarm.join_token(node_type))
        except DockerException:
            # log.debug(e)
            return None

    @staticmethod
    def deploy() -> None:
        docker.stack.deploy(name=Configuration.project, compose_files=COMPOSE_FILE)

    @staticmethod
    def status() -> None:
        nodes: Dict[str, str] = {}
        print("====== Nodes ======")
        for node in docker.node.list():
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

        tasks: Dict[str, List[Task]] = {}

        try:
            for task in docker.stack.ps(Configuration.project):
                tasks.setdefault(task.service_id, [])
                tasks[task.service_id].append(task)
        except DockerException:
            pass

        print("")

        if not tasks:
            log.info("No service is running")
            return

        print("====== Services ======")

        for service in docker.service.list():
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

    @staticmethod
    def remove() -> None:
        docker.stack.remove(Configuration.project)
