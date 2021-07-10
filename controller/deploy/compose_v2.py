from pathlib import Path
from typing import List

from controller import COMPOSE_FILE, log
from controller.deploy.compose import Compose as ComposeLegacy


class Compose:
    def __init__(self) -> None:
        pass

    def dump_config(self, compose_files: List[Path], services: List[str]) -> None:
        dc = ComposeLegacy(files=compose_files)
        compose_config = dc.config(relative_paths=True)
        dc.dump_config(compose_config, COMPOSE_FILE, services)
        log.debug("Compose configuration dumped on {}", COMPOSE_FILE)
