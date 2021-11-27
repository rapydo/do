"""
This module will test basic app functionalities, like iteraction with typer
and the checks of the current folder (git repo and rapydo structure required)
"""
import os
import tempfile

from faker import Faker

from controller import __version__, colors
from tests import (
    Capture,
    create_project,
    exec_command,
    execute_outside,
    init_project,
    random_project_name,
)


def test_base(capfd: Capture, faker: Faker) -> None:

    execute_outside(capfd, "version")

    exec_command(
        capfd,
        "--version",
        f"rapydo version: {__version__}",
    )

    project = random_project_name(faker)

    exec_command(
        capfd,
        f"--invalid-option create {project}",
        "Error: No such option: --invalid-option",
    )

    exec_command(capfd, "rapydo", "Usage")

    create_project(
        capfd=capfd,
        name=project,
        auth="postgres",
        frontend="no",
    )
    init_project(capfd)

    exec_command(
        capfd,
        "version",
        f"rapydo: {colors.GREEN}{__version__}",
        f"required rapydo: {colors.GREEN}{__version__}",
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

    exec_command(
        capfd,
        "--remote invalid check -i main --no-git",
        "Could not resolve hostname invalid: ",
    )

    exec_command(
        capfd,
        "--remote invalid@invalid check -i main --no-git",
        # Temporary failure in name resolution depends by the OS
        # on alpine che message is: Name does not resolve
        # "Could not resolve hostname invalid: Temporary failure in name resolution",
        "Could not resolve hostname invalid: ",
    )

    exec_command(
        capfd,
        "-s backend check -i main --no-git --no-builds",
        # warnings are not catched !?
        # "-s option is going to be replaced by rapydo <command> service",
    )

    exec_command(
        capfd,
        "start backend",
        "Enabled services: ['backend']",
    )

    exec_command(
        capfd,
        "start backend postgres",
        "Enabled services: ['backend', 'postgres']",
    )

    exec_command(
        capfd,
        "start backend postgres _backend",
        "Enabled services: ['postgres']",
    )

    exec_command(
        capfd,
        "start backend postgres _invalid",
        "No such service: invalid",
    )

    exec_command(
        capfd,
        "-e ACTIVATE_FAIL2BAN start fail2ban",
        "Invalid enviroment, missing value in ACTIVATE_FAIL2BAN",
    )
