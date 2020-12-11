import os
import tempfile

from controller import __version__
from tests import create_project, exec_command


def test_base(capfd):
    exec_command(
        capfd,
        "--version",
        f"rapydo version: {__version__}",
    )

    exec_command(
        capfd,
        "--invalid-option create first",
        "Error: no such option: --invalid-option",
    )

    exec_command(capfd, "rapydo", "Usage")

    create_project(
        capfd=capfd, name="latest", auth="postgres", frontend="no", init=True
    )

    folder = os.getcwd()
    # Tests from a subfolder
    os.chdir("projects")
    exec_command(
        capfd,
        "-p latest check -i main --no-git --no-builds",
        "You are not in the main folder, please change your working dir",
        "Found a valid parent folder:",
        "Suggested command: cd ..",
    )

    os.chdir("latest")
    exec_command(
        capfd,
        "-p latest check -i main --no-git --no-builds",
        "You are not in the main folder, please change your working dir",
        "Found a valid parent folder:",
        "Suggested command: cd ../..",
    )

    # Tests from outside the folder
    os.chdir(tempfile.gettempdir())
    exec_command(
        capfd,
        "check -i main",
        "You are not in a git repository",
        "Please note that this command only works from inside a rapydo-like repository",
        "Verify that you are in the right folder, now you are in:",
    )

    os.chdir(folder)
