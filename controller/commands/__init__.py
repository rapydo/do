from importlib import import_module
from pathlib import Path


def load_commands():

    commands_folder = Path(__file__).resolve().parent

    for c in commands_folder.glob("[!_|.]*.py"):

        import_module(f"controller.commands.{c.stem}")
