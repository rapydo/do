"""
Integration with Docker swarmg
"""

from typing import Optional

from python_on_whales import docker
from python_on_whales.utils import DockerException

from controller import COMPOSE_FILE
from controller.app import Configuration


class Swarm:
    def __init__(self):
        pass

    def init(self) -> None:
        docker.swarm.init()

    def leave(self) -> None:
        docker.swarm.leave(force=True)

    def get_token(self, node_type: str = "manager") -> Optional[str]:
        try:
            return str(docker.swarm.join_token(node_type))
        except DockerException:
            # log.debug(e)
            return None

    def deploy(self) -> None:
        docker.stack.deploy(name=Configuration.project, compose_files=COMPOSE_FILE)

    def remove(self) -> None:
        docker.stack.remove(Configuration.project)
