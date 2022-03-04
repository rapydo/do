from typing import Tuple

from controller.app import Application
from controller.deploy.docker import Docker
from controller.utilities import services

SERVICE_NAME = __name__
# PASSWORD_VARIABLES = ["ALCHEMY_PASSWORD", "MYSQL_ROOT_PASSWORD"]
# MYSQL_ROOT_PASSWORD change is not supported yet
PASSWORD_VARIABLES = ["ALCHEMY_PASSWORD"]
IS_RUNNING_NEEDED = True


def password(container: Tuple[str, str], old_password: str, new_password: str) -> None:
    # https://dev.mysql.com/doc/refman/8.0/en/set-password.html

    docker = Docker()

    user = Application.env.get("ALCHEMY_USER")
    pwd = Application.env.get("MYSQL_ROOT_PASSWORD")
    db = Application.env.get("ALCHEMY_DB")

    docker.exec_command(
        container,
        user=services.get_default_user(SERVICE_NAME),
        command=f"""
            mysql -uroot -p\"{pwd}\" -D\"{db}\" -e
                "ALTER USER '{user}'@'%' IDENTIFIED BY '{new_password}';"
            """,
    )
