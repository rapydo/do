import os
from glob import glob
from importlib import import_module


def load_commands():

    commands_folder = os.path.dirname(os.path.abspath(__file__))

    for c in glob(f"{commands_folder}/[!_|.]*.py"):

        c = os.path.splitext(os.path.basename(c))[0]

        import_module(f"controller.commands.{c}")
