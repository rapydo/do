import os
import pwd

from plumbum import local
from plumbum.commands.processes import ProcessExecutionError

from controller import log


def execute_command(command, parameters):
    try:

        # Pattern in plumbum library for executing a shell command
        command = local[command]
        log.verbose("Executing command {} {}", command, parameters)
        return command(parameters)

    except ProcessExecutionError as e:
        raise e


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
