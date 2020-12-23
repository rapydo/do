"""
This module will test basic app functionalities, like iteraction with typer
and the checks of the current folder (git repo and rapydo structure required)
"""
import os
import tempfile

from controller import __version__
from tests import create_project, exec_command, random_project_name


def test_base(capfd, fake):

    exec_command(
        capfd,
        "--version",
        f"rapydo version: {__version__}",
    )

    project = random_project_name(fake)

    exec_command(
        capfd,
        f"--invalid-option create {project}",
        "Error: no such option: --invalid-option",
    )

    exec_command(capfd, "rapydo", "Usage")

    create_project(
        capfd=capfd,
        name=project,
        auth="postgres",
        frontend="no",
        init=True,
        pull=False,
        start=False,
    )

    exec_command(
        capfd,
        "version",
        f"rapydo: \033[1;32m{__version__}",
        f"required rapydo: \033[1;32m{__version__}",
    )

    # boolean variables mostly deprecated in 1.0
    # Use the old-fashioned 0/1 integers
    # Backend and Frontend use different booleans due to Python vs Javascript
    # 0/1 is a much more portable value to prevent true|True|"true"
    # This fixes troubles in setting boolean values only used by Angular
    # (expected true|false) or used by Pyton (expected True|False)

    # Test adding strings True|False|true|false
    exec_command(
        capfd,
        "-e ENABLE_FOOTER=true check -i main --no-git --no-builds",
        "Deprecated value for ENABLE_FOOTER, convert true to 1",
    )
    exec_command(
        capfd,
        "-e ENABLE_FOOTER=True check -i main --no-git --no-builds",
        "Deprecated value for ENABLE_FOOTER, convert True to 1",
    )
    exec_command(
        capfd,
        "-e ENABLE_FOOTER=false check -i main --no-git --no-builds",
        "Deprecated value for ENABLE_FOOTER, convert false to 0",
    )
    exec_command(
        capfd,
        "-e ENABLE_FOOTER=False check -i main --no-git --no-builds",
        "Deprecated value for ENABLE_FOOTER, convert False to 0",
    )

    # Test adding boolean True|False
    with open(".projectrc", "a") as f:
        f.write("\n      ENABLE_FOOTER: True\n")
    exec_command(
        capfd,
        "check -i main --no-git --no-builds",
        "Deprecated value for ENABLE_FOOTER, convert True to 1",
    )

    with open(".projectrc", "a") as f:
        f.write("\n      ENABLE_FOOTER: False\n")
    exec_command(
        capfd,
        "check -i main --no-git --no-builds",
        "Deprecated value for ENABLE_FOOTER, convert False to 0",
    )

    folder = os.getcwd()
    # Tests from a subfolder
    os.chdir("projects")
    exec_command(
        capfd,
        "check -i main --no-git --no-builds",
        "You are not in the main folder, please change your working dir",
        "Found a valid parent folder:",
        "Suggested command: cd ..",
    )

    os.chdir(project)
    exec_command(
        capfd,
        "check -i main --no-git --no-builds",
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
