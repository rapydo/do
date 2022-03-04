from typing import Tuple

from controller.deploy.docker import Docker
from controller.utilities import services

SERVICE_NAME = __name__
PASSWORD_VARIABLES = ["NEO4J_PASSWORD"]
IS_RUNNING_NEEDED = True


def password(container: Tuple[str, str], old_password: str, new_password: str) -> None:
    docker = Docker()

    docker.exec_command(
        container,
        user=services.get_default_user(SERVICE_NAME),
        command=f"""bin/cypher-shell \"
            ALTER CURRENT USER
            SET PASSWORD
            FROM '{old_password}'
            TO '{new_password}';
        \"""",
    )
