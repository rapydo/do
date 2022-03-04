from typing import Tuple

from controller.deploy.docker import Docker
from controller.utilities import services

SERVICE_NAME = __name__
PASSWORD_VARIABLES = ["AUTH_DEFAULT_PASSWORD"]
IS_RUNNING_NEEDED = True


def password(container: Tuple[str, str], old_password: str, new_password: str) -> None:

    docker = Docker()
    # restapi init need the env variable to be updated but can't be done after
    # the restart because it often fails because unable to re-connect to
    # services in a short time and some long sleep would be needed
    # => applied a workaround to be able to execute it before the restart
    docker = Docker()
    docker.exec_command(
        container,
        user=services.get_default_user(SERVICE_NAME),
        command=f"""/bin/bash -c '
            AUTH_DEFAULT_PASSWORD=\"{new_password}\"
                restapi init --force-user
            '
            """,
    )
