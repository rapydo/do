import os
import sys
from pathlib import Path

from loguru import logger as log

__version__ = "0.9"

DATA_FOLDER = Path("data").resolve()
LOGS_FOLDER = DATA_FOLDER.joinpath("logs")

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
        log.add(LOGS_FILE, level="WARNING", rotation="1 week", retention="4 weeks")
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
