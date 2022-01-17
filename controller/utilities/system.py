import os
import socket
from typing import List

from plumbum import local
from plumbum.commands.processes import CommandNotFound, ProcessExecutionError

from controller import log

GB = 1_073_741_824
MB = 1_048_576
KB = 1024


class ExecutionException(Exception):
    pass


def execute_command(command: str, parameters: List[str]) -> str:
    try:

        # Pattern in plumbum library for executing a shell command
        local_command = local[command]
        log.debug("Executing command {} {}", command, " ".join(parameters))
        return str(local_command(parameters))
    except CommandNotFound:
        raise ExecutionException(f"Command not found: {command}")

    except ProcessExecutionError:
        raise ExecutionException(
            f"Cannot execute command: {command} {' '.join(parameters)}"
        )

    # raised on Windows
    except OSError:  # pragma: no cover
        raise ExecutionException(f"Cannot execute: {command}")


def get_username(uid: int) -> str:
    try:
        import pwd

        return pwd.getpwuid(uid).pw_name
    # Can fail on Windows
    except ImportError as e:  # pragma: no cover
        log.debug(e)
        return str(uid)


def get_current_uid() -> int:
    try:
        return os.getuid()
    # Can fail on Windows
    except AttributeError as e:  # pragma: no cover
        log.debug(e)
        return 0


def get_current_gid() -> int:
    try:
        return os.getgid()
    # Can fail on Windows
    except AttributeError as e:  # pragma: no cover
        log.debug(e)
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


# This is no longer needed
def str_to_bytes(text: str) -> float:

    text = text.upper()

    value: str = text
    unit: int = 1

    if text.endswith("G"):
        value = text[:-1]
        unit = GB

    if text.endswith("M"):
        value = text[:-1]
        unit = MB

    if text.endswith("K"):
        value = text[:-1]
        unit = KB

    if text.endswith("GB"):
        value = text[:-2]
        unit = GB

    if text.endswith("MB"):
        value = text[:-2]
        unit = MB

    if text.endswith("KB"):
        value = text[:-2]
        unit = KB

    if not value.isnumeric():
        raise AttributeError(f"Invalid float value {value}")

    return float(value) * unit


def get_local_ip(production: bool = False) -> str:
    if production:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        return str(s.getsockname()[0])

    return "127.0.0.1"
