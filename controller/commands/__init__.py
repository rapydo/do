from importlib import import_module
from pathlib import Path

from controller import SWARM_MODE


def load_commands() -> None:

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
