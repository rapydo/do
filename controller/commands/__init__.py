"""
All core commands implemented in RAPyDo
"""

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from types import ModuleType
from typing import Dict, Optional

from controller import PROJECT_DIR

BACKUP_MODULES: Dict[str, ModuleType] = {}
RESTORE_MODULES: Dict[str, ModuleType] = {}
PASSWORD_MODULES: Dict[str, ModuleType] = {}
TUNING_MODULES: Dict[str, ModuleType] = {}


def load_module(path: Path) -> Dict[str, ModuleType]:

    # Initially it was:
    # for c in commands_folder.glob("[!_|.]*.py"):
    #     import_module(f"controller.commands.{c.stem}")

    loaded_modules: Dict[str, ModuleType] = {}
    if path.is_dir():
        for c in path.glob("[!_|.]*.py"):
            spec = spec_from_file_location(c.stem, c)
            if spec and spec.loader:
                command = module_from_spec(spec)
                # "_LoaderProtocol" has no attribute "exec_module"
                # https://issueexplorer.com/issue/python/typeshed/6163
                spec.loader.exec_module(command)
                loaded_modules[c.stem] = command

    return loaded_modules


def load_commands(project: Optional[str]) -> None:

    # re-initialization needed for tests
    BACKUP_MODULES.clear()
    RESTORE_MODULES.clear()
    PASSWORD_MODULES.clear()
    TUNING_MODULES.clear()

    commands_folder = Path(__file__).resolve().parent
    BACKUP_MODULES.update(load_module(commands_folder.joinpath("backup_modules")))
    RESTORE_MODULES.update(load_module(commands_folder.joinpath("restore_modules")))
    PASSWORD_MODULES.update(load_module(commands_folder.joinpath("password_modules")))
    TUNING_MODULES.update(load_module(commands_folder.joinpath("tuning_modules")))

    # Do custom commands exist?
    if project:
        custom_commands = PROJECT_DIR.joinpath(project, "commands")
        load_module(custom_commands)

        BACKUP_MODULES.update(load_module(custom_commands.joinpath("backup_modules")))
        RESTORE_MODULES.update(load_module(custom_commands.joinpath("restore_modules")))
        PASSWORD_MODULES.update(
            load_module(custom_commands.joinpath("password_modules"))
        )
        TUNING_MODULES.update(load_module(custom_commands.joinpath("tuning_modules")))

    load_module(commands_folder)

    # Do not import outside, otherwise it will lead to a circular import:
    # cannot import name 'Configuration' from partially initialized module
    from controller.app import Configuration

    if Configuration.swarm_mode:
        load_module(commands_folder.joinpath("swarm"))
    else:
        load_module(commands_folder.joinpath("compose"))
