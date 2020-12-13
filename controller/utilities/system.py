import os
import pwd
from typing import List

from plumbum import local
from plumbum.commands.processes import CommandNotFound, ProcessExecutionError

from controller import log

GB = 1_073_741_824
MB = 1_048_576
KB = 1024


class ExecutionException(BaseException):
    pass


def execute_command(command: str, parameters: List[str]) -> str:
    try:

        # Pattern in plumbum library for executing a shell command
        local_command = local[command]
        log.debug("Executing command {} {}", command, parameters)
        return str(local_command(parameters))
    except CommandNotFound:
        raise ExecutionException(f"Command not found: {command}")

    except ProcessExecutionError:
        raise ExecutionException(
            "Cannot execute command: {} {}".format(command, " ".join(parameters))
        )


def get_username(uid: int) -> str:
    try:
        return pwd.getpwuid(uid).pw_name
    # Can fail on Windows
    except ImportError as e:  # pragma: no cover
        log.warning(e)
        return str(uid)


def get_current_uid() -> int:
    try:
        return os.getuid()
    # Can fail on Windows
    except AttributeError as e:  # pragma: no cover
        log.warning(e)
        return 0


def get_current_gid() -> int:
    try:
        return os.getgid()
    # Can fail on Windows
    except AttributeError as e:  # pragma: no cover
        log.warning(e)
        return 0


def bytes_to_str(value: float) -> str:

    if value >= GB:
        value /= GB
        unit = "GB"
    elif value >= MB:
        value /= MB
        unit = "MB"
    elif value >= KB:
        value /= KB
        unit = "KB"
    else:
        unit = ""

    return f"{int(round(value, 0))}{unit}"
