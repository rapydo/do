import os
from importlib import import_module
from pathlib import Path


def load_commands() -> None:

    swarm_mode = os.environ.get("SWARM_MODE", "0") == "1"
    commands_folder = Path(__file__).resolve().parent
    swarm_folder = commands_folder.joinpath("swarm")

    for c in commands_folder.glob("[!_|.]*.py"):
        if swarm_mode and swarm_folder.joinpath(c.stem).with_suffix(".py").exists():
            import_module(f"controller.commands.swarm.{c.stem}")
        else:
            import_module(f"controller.commands.{c.stem}")
