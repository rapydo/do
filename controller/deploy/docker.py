from typing import Optional

from python_on_whales import DockerClient

from controller import print_and_exit
from controller.app import Configuration


class Docker:
    def __init__(self) -> None:

        self.client = DockerClient(host=self.get_engine())

    @classmethod
    def get_engine(cls) -> Optional[str]:
        if not Configuration.remote_engine:
            return None

        if not cls.validate_remote_engine(Configuration.remote_engine):
            print_and_exit(
                "Invalid remote host {}, expected user@ip-or-hostname",
                Configuration.remote_engine,
            )

        return f"ssh://{Configuration.remote_engine}"

    @staticmethod
    def validate_remote_engine(host: str) -> bool:
        if "@" not in host:
            return False
        # TODO: host should be validated as:
        # user @ ip | host
        return True
