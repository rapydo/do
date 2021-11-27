import os
import sys
from pathlib import Path
from typing import Dict, NoReturn, Union

from colorama import Fore as colors
from loguru import logger as log
from python_on_whales.components.compose.models import ComposeConfigService

ComposeServices = Dict[str, ComposeConfigService]

__version__ = "2.1"

__all__ = [colors]

LOGS_FOLDER = Path("data", "logs").resolve()
LOG_RETENTION = os.getenv("LOG_RETENTION", "180")
LOG_FORMAT = os.getenv("RAPYDO_LOG_FORMAT", "simple")
TABLE_FORMAT = "simple"  # plain, simple, pretty, presto

LOGS_FILE = None
if LOGS_FOLDER.is_dir():
    LOGS_FILE = LOGS_FOLDER.joinpath("rapydo-controller.log")

# log.level("VERBOSE", no=1, color="<fg #666>")
log.level("INFO", color="<green>")

log.remove()

TESTING = os.getenv("TESTING", "0") == "1"

fmt = "<fg #666>{time:YYYY-MM-DD HH:mm:ss,SSS}</fg #666> "

if LOG_FORMAT == "full":  # pragma: no cover
    fmt += "[<level>{level}</level> "
    fmt += "<fg #666>{name}:{line}</fg #666>] "
else:
    fmt += "<level>{level:8}</level> "

fmt += "<fg #FFF>{message}</fg #FFF>"

log.add(sys.stderr, format=fmt)

if LOGS_FILE is not None:
    try:
        log.add(
            LOGS_FILE,
            level=0,
            rotation="1 week",
            retention=f"{LOG_RETENTION} days",
            format="{time:YYYY-MM-DD HH:mm:ss,SSS} <level>{level:8}</level> {message}",
            colorize=False,
            filter=lambda record: record["level"].no >= log.level("WARNING").no
            or "log_to_file" in record["extra"],
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
COMPOSE_FILE_VERSION = "3.9"

SWARM_MODE = os.environ.get("SWARM_MODE", "0") == "1"
REGISTRY = "registry"

EnvType = Union[None, str, int, float]


def print_and_exit(
    message: str, *args: Union[str, Path], **kwargs: Union[str, Path]
) -> NoReturn:
    log.critical(message, *args, **kwargs)
    sys.exit(1)


def RED(msg: str) -> str:
    return f"{colors.RED}{msg}{colors.RESET}"


def YELLOW(msg: str) -> str:
    return f"{colors.YELLOW}{msg}{colors.RESET}"


def GREEN(msg: str) -> str:
    return f"{colors.GREEN}{msg}{colors.RESET}"
