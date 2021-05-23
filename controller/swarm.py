"""
Integration with Docker swarmg
"""

# from pathlib import Path
from typing import Optional

from python_on_whales import docker
from python_on_whales.utils import DockerException


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
