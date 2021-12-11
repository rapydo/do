from typing import Tuple

from controller.app import Application
from controller.deploy.docker import Docker
from controller.utilities import services

SERVICE_NAME = __name__
PASSWORD_VARIABLES = ["RABBITMQ_PASSWORD"]
IS_RUNNING_NEEDED = True


def password(container: Tuple[str, str], old_password: str, new_password: str) -> None:
    docker = Docker()
    user = Application.env.get("RABBITMQ_USER")
    docker.exec_command(
        container,
        user=services.get_default_user(SERVICE_NAME),
        command=f'rabbitmqctl change_password "{user}" "{new_password}"',
    )
