from typing import Tuple

SERVICE_NAME = __name__
PASSWORD_VARIABLES = ["FLOWER_PASSWORD"]
IS_RUNNING_NEEDED = False


def password(container: Tuple[str, str], old_password: str, new_password: str) -> None:
    pass
