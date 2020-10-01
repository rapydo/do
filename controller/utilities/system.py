import os
import pwd

from plumbum import local
from plumbum.commands.processes import CommandNotFound, ProcessExecutionError

from controller import log

GB = 1_073_741_824
MB = 1_048_576
KB = 1024


class ExecutionException(BaseException):
    pass


def execute_command(command, parameters):
    try:

        # Pattern in plumbum library for executing a shell command
        command = local[command]
        log.verbose("Executing command {} {}", command, parameters)
        return command(parameters)
    except CommandNotFound:
        raise ExecutionException(f"Command not found: {command}")

    except ProcessExecutionError:
        raise ExecutionException(
            "Cannot execute {} {}".format(command, " ".join(parameters))
        )


def get_username(uid):
    try:
        return pwd.getpwuid(uid).pw_name
    # Can fail on Windows
    except ImportError as e:  # pragma: no cover
        log.warning(e)
        return str(uid)


def get_current_uid():
    try:
        return os.getuid()
    # Can fail on Windows
    except AttributeError as e:  # pragma: no cover
        log.warning(e)
        return 0


def get_current_gid():
    try:
        return os.getgid()
    # Can fail on Windows
    except AttributeError as e:  # pragma: no cover
        log.warning(e)
        return 0


def bytes_to_str(value):

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
