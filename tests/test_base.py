"""
This module will test basic app functionalities, like iteraction with typer
and the checks of the current folder (git repo and rapydo structure required)
"""
import os
import tempfile

from faker import Faker

from controller import __version__
from tests import Capture, create_project, exec_command, random_project_name


def test_base(capfd: Capture, faker: Faker) -> None:

    exec_command(
        capfd,
        "--version",
        f"rapydo version: {__version__}",
    )

    project = random_project_name(faker)

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

    auth_envs = "-e AUTH_DEFAULT_PASSWORD=short"
    alchemy_envs = " -e ALCHEMY_USER=sqluser -e ALCHEMY_PASSWORD=short"
    exec_command(
        capfd,
        f"--prod {auth_envs} {alchemy_envs} check -i main --no-git --no-builds",
        "AUTH_DEFAULT_PASSWORD is set with a short password",
        "ALCHEMY_PASSWORD is set with a short password",
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
