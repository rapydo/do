from typing import Tuple

from controller.app import Application
from controller.deploy.docker import Docker
from controller.utilities import services

SERVICE_NAME = __name__
PASSWORD_VARIABLES = ["ALCHEMY_PASSWORD"]
IS_RUNNING_NEEDED = True


def password(container: Tuple[str, str], old_password: str, new_password: str) -> None:

    docker = Docker()
    # Interactively:
    # \password username
    # Non interactively:
    # https://ubiq.co/database-blog/how-to-change-user-password-in-postgresql
    user = Application.env.get("ALCHEMY_USER")
    db = Application.env.get("ALCHEMY_DB")
    docker.exec_command(
        container,
        user=services.get_default_user(SERVICE_NAME),
        command=f"""
            psql -U {user} -d {db} -c \"
                ALTER USER {user} WITH PASSWORD \'{new_password}\';
            \"
        """,
    )
