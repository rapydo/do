"""
Integration with Docker swarmg
"""

# from pathlib import Path
from typing import Optional

from python_on_whales import docker
from python_on_whales.utils import DockerException

# from controller import COMPOSE_ENVIRONMENT_FILE, log
# from controller.app import Configuration


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

    # def deploy(self, compose_files: List[Path]) -> None:
    #     log.critical(COMPOSE_ENVIRONMENT_FILE.resolve())
    #     docker.stack.deploy(
    #         name=Configuration.project,
    #         compose_files=compose_files,
    #         env_files=[COMPOSE_ENVIRONMENT_FILE.resolve()]
    #     )
