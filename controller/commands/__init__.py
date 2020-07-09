import os
from importlib import import_module


def load_commands():

    commands_folder = os.path.dirname(os.path.abspath(__file__))

    for c in os.listdir(commands_folder):

        if c.startswith("_") or c.startswith("."):
            continue
        if not c.endswith(".py"):
            continue

        c = os.path.splitext(c)[0]

        import_module(f"controller.commands.{c}")
