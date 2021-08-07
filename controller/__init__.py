import os
import sys
from pathlib import Path
from typing import Any, Dict, NoReturn, Union

from loguru import logger as log

__version__ = "2.1"

LOGS_FOLDER = Path("data", "logs").resolve()
LOG_RETENTION = os.getenv("LOG_RETENTION", "180")

LOGS_FILE = None
if LOGS_FOLDER.is_dir():
    LOGS_FILE = LOGS_FOLDER.joinpath("rapydo-controller.log")

# log.level("VERBOSE", no=1, color="<fg #666>")
log.level("INFO", color="<green>")

log.remove()

if os.getenv("TESTING", "0") == "1":
    fmt = "{message}"
    colorize = False
else:  # pragma: no cover
    fmt = "<fg #FFF>{time:YYYY-MM-DD HH:mm:ss,SSS}</fg #FFF> "
    fmt += "[<level>{level}</level> "
    fmt += "<fg #666>{name}:{line}</fg #666>] "
    fmt += "<fg #FFF>{message}</fg #FFF>"
    colorize = True

log.add(sys.stderr, colorize=colorize, format=fmt)

if LOGS_FILE is not None:
    try:
        log.add(
            LOGS_FILE,
            level="WARNING",
            rotation="1 week",
            retention=f"{LOG_RETENTION} days",
        )
    except PermissionError as e:  # pragma: no cover
        log.error(e)
        LOGS_FILE = None

COMPOSE_ENVIRONMENT_FILE = Path(".env")
SUBMODULES_DIR = Path("submodules")
PROJECT_DIR = Path("projects")
TEMPLATE_DIR = Path("templates")

CONFS_DIR = Path(__file__).resolve().parent.joinpath("confs")

PLACEHOLDER = "**PLACEHOLDER**"
PROJECTRC = Path(".projectrc")
# PROJECTRC_ALTERNATIVE = ".project.yml"
DATAFILE = Path(".rapydo")
EXTENDED_PROJECT_DISABLED = "no_extended_project"
CONTAINERS_YAML_DIRNAME = "confs"
COMPOSE_FILE = Path("docker-compose.yml")
COMPOSE_FILE_VERSION = "3.8"

ComposeConfig = Dict[str, Any]

SWARM_MODE = os.environ.get("SWARM_MODE", "0") == "1"

EnvType = Union[None, str, int, float]


def print_and_exit(
    message: str, *args: Union[str, Path], **kwargs: Union[str, Path]
) -> NoReturn:
    log.critical(message, *args, **kwargs)
    sys.exit(1)
