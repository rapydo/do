from importlib import import_module
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from typing import Optional

from controller import PROJECT_DIR, SWARM_MODE


def load_commands(project: Optional[str]) -> None:

    commands_folder = Path(__file__).resolve().parent
    compose_folder = commands_folder.joinpath("compose")
    swarm_folder = commands_folder.joinpath("swarm")

    for c in commands_folder.glob("[!_|.]*.py"):
        import_module(f"controller.commands.{c.stem}")

    if SWARM_MODE:
        for c in swarm_folder.glob("[!_|.]*.py"):
            import_module(f"controller.commands.swarm.{c.stem}")
    else:
        for c in compose_folder.glob("[!_|.]*.py"):
            import_module(f"controller.commands.compose.{c.stem}")

    # Do custom commands exist?
    if project:
        custom_folder = PROJECT_DIR.joinpath(project, "commands").resolve()

        if custom_folder.is_dir():
            for c in custom_folder.glob("[!_|.]*.py"):
                spec = spec_from_file_location("module.name", c)
                if spec and spec.loader:
                    custom_command = module_from_spec(spec)
                    # "_LoaderProtocol" has no attribute "exec_module"
                    # https://issueexplorer.com/issue/python/typeshed/6163
                    spec.loader.exec_module(custom_command)  # type: ignore
