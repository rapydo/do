import os
import sys
from importlib import import_module, reload


def load_commands():

    commands_folder = os.path.dirname(os.path.abspath(__file__))

    for c in os.listdir(commands_folder):

        if c.startswith("_") or c.startswith("."):
            continue
        if not c.endswith(".py"):
            continue

        c = os.path.splitext(c)[0]

        modulename = f"controller.commands.{c}"
        # This is needed to reload the App during the tests
        already_loaded = modulename in sys.modules
        m = import_module(modulename)

        if already_loaded:
            reload(m)
