import os
import socket
from typing import Optional, Union

from controller import log

GB = 1_073_741_824
MB = 1_048_576
KB = 1024


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
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            return str(s.getsockname()[0])

    return "127.0.0.1"


def to_int(value: Union[int, str]) -> Optional[int]:
    try:
        return int(value)
    except ValueError:
        return None
