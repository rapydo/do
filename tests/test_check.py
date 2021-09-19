"""
This module will test the check command
"""
import os
import shutil
from pathlib import Path

from controller import SWARM_MODE, __version__, colors
from controller.deploy.swarm import Swarm
from controller.utilities import git
from tests import (
    Capture,
    TemporaryRemovePath,
    create_project,
    exec_command,
    init_project,
)


def test_base(capfd: Capture) -> None:

    create_project(
        capfd=capfd,
        name="third",
        auth="postgres",
        frontend="angular",
    )
    init_project(capfd)

    repo = git.get_repo("submodules/http-api")
    git.switch_branch(repo, "0.7.6")
    exec_command(
        capfd,
        "check -i main",
        f"http-api: wrong branch 0.7.6, expected {__version__}",
        f"You can use {colors.RED}rapydo init{colors.RESET} to fix it",
    )
    init_project(capfd)

    with TemporaryRemovePath(Path("data")):
        exec_command(
            capfd,
            "check -i main --no-git --no-builds",
            "Folder not found: data",
            "Please note that this command only works from inside a rapydo-like repo",
            "Verify that you are in the right folder, now you are in: ",
        )

    with TemporaryRemovePath(Path("projects/third/builds")):
        exec_command(
            capfd,
            "check -i main --no-git --no-builds",
            "Project third is invalid: required folder not found projects/third/builds",
        )

    with TemporaryRemovePath(Path(".gitignore")):
        exec_command(
            capfd,
            "check -i main --no-git --no-builds",
            "Project third is invalid: required file not found .gitignore",
        )

    # Add a custom image to extend base backend image:
    with open("projects/third/confs/commons.yml", "a") as f:
        f.write(
            """
services:
  backend:
    build: ${PROJECT_DIR}/builds/backend
    image: third/backend:${RAPYDO_VERSION}

    """
        )

    os.makedirs("projects/third/builds/backend")
    with open("projects/third/builds/backend/Dockerfile", "w+") as f:
        f.write(
            f"""
FROM rapydo/backend:{__version__}
RUN mkdir xyz
"""
        )

    # Skipping main because we are on a fake git repository
    exec_command(
        capfd,
        "check -i main",
        f" image, execute {colors.RED}rapydo pull",
        f" image, execute {colors.RED}rapydo build",
        "Checks completed",
    )

    exec_command(
        capfd,
        "--stack invalid check -i main",
        "Failed to read projects/third/confs/invalid.yml: File does not exist",
    )

    os.mkdir("submodules/rapydo-confs")
    exec_command(
        capfd,
        "check -i main --no-git --no-builds",
        "Project third contains an obsolete file or folder: submodules/rapydo-confs",
    )

    shutil.rmtree("submodules/rapydo-confs")

    # Test selection with two projects
    create_project(
        capfd=capfd,
        name="justanother",
        auth="postgres",
        frontend="no",
    )

    os.remove(".projectrc")

    exec_command(
        capfd,
        "check -i main --no-git --no-builds",
        "Multiple projects found, please use --project to specify one of the following",
    )

    # Test with zero projects
    with TemporaryRemovePath(Path("projects")):
        os.mkdir("projects")
        exec_command(
            capfd,
            "check -i main --no-git --no-builds",
            "No project found (projects folder is empty?)",
        )
        shutil.rmtree("projects")

    exec_command(
        capfd,
        "-p third check -i main --no-git --no-builds",
        "Checks completed",
    )

    # Numbers are not allowed as first characters
    pname = "2invalidcharacter"
    os.makedirs(f"projects/{pname}")
    exec_command(
        capfd,
        f"-p {pname} check -i main --no-git --no-builds",
        "Wrong project name, found invalid characters: 2",
    )
    shutil.rmtree(f"projects/{pname}")

    invalid_characters = {
        "_": "_",
        "-": "-",
        "C": "C",
        # Invalid characters in output are ordered
        # Numbers are allowed if not leading
        "_C-2": "-C_",
    }
    # Check invalid and reserved project names
    for invalid_key, invalid_value in invalid_characters.items():
        pname = f"invalid{invalid_key}character"
        os.makedirs(f"projects/{pname}")
        exec_command(
            capfd,
            f"-p {pname} check -i main --no-git --no-builds",
            f"Wrong project name, found invalid characters: {invalid_value}",
        )
        shutil.rmtree(f"projects/{pname}")

    os.makedirs("projects/celery")
    exec_command(
        capfd,
        "-p celery check -i main --no-git --no-builds",
        "You selected a reserved name, invalid project name: celery",
    )
    shutil.rmtree("projects/celery")

    exec_command(
        capfd,
        "-p fourth check -i main --no-git --no-builds",
        "Wrong project fourth",
        "Select one of the following: ",
    )

    # Test init of data folders
    shutil.rmtree("data/logs")
    assert not os.path.isdir("data/logs")
    # Let's restore .projectrc and data/logs
    init_project(capfd, "--project third")

    assert os.path.isdir("data/logs")
    exec_command(
        capfd,
        "check -i main --no-git --no-builds",
        "Checks completed",
    )

    # Test dirty repo
    fin = open("submodules/do/new_file", "wt+")
    fin.write("xyz")
    fin.close()

    exec_command(
        capfd,
        "check -i main",
        "You have unstaged files on do",
        "Untracked files:",
        "submodules/do/new_file",
    )

    with open(".gitattributes", "a") as a_file:
        a_file.write("\n")
        a_file.write("# new line")

    exec_command(
        capfd,
        "check -i main",
        ".gitattributes changed, "
        f"please execute {colors.RED}rapydo upgrade --path .gitattributes",
    )

    exec_command(
        capfd,
        "--prod check -i main --no-git --no-builds",
        "The following variables are missing in your configuration",
        "You can fix this error by updating your .projectrc file",
        "Do you want some random passwords?",
    )

    # Default ALCHEMY_PASSWORD has as score of 2
    exec_command(
        capfd,
        "-e MIN_PASSWORD_SCORE=3 check -i main --no-git --no-builds",
        "The password used in ALCHEMY_PASSWORD is weak",
    )
    exec_command(
        capfd,
        "-e MIN_PASSWORD_SCORE=4 check -i main --no-git --no-builds",
        "The password used in ALCHEMY_PASSWORD is very weak",
    )
    exec_command(
        capfd,
        "-e MIN_PASSWORD_SCORE=5 check -i main --no-git --no-builds",
        "The password used in ALCHEMY_PASSWORD is extremely weak",
    )

    exec_command(
        capfd,
        "--prod init -f",
        "Created default .projectrc file",
        "Project initialized",
    )

    exec_command(
        capfd,
        "--prod check -i main --no-git --no-builds",
        "Checks completed",
    )

    if SWARM_MODE:
        # Skipping main because we are on a fake git repository
        exec_command(
            capfd,
            "check -i main",
            "Swarm is correctly initialized",
            "Checks completed",
        )

        swarm = Swarm()
        swarm.leave()

        exec_command(
            capfd,
            "check -i main",
            f"Swarm is not initialized, please execute {colors.RED}rapydo init",
        )
        exec_command(
            capfd,
            "init",
            "Swarm is now initialized",
            "Project initialized",
        )
        exec_command(
            capfd,
            "check -i main",
            "Swarm is correctly initialized",
            "Checks completed",
        )

        check = "check -i main --no-git --no-builds"

        exec_command(
            capfd,
            f"-e ASSIGNED_MEMORY_BACKEND=50G {check}",
            "Your deployment requires 50GB of RAM but your nodes only have",
            # The error does not halt the checks execution
            "Checks completed",
        )

        exec_command(
            capfd,
            f"-e ASSIGNED_CPU_BACKEND=50 {check}",
            "Your deployment requires ",
            " cpus but your nodes only have ",
            # The error does not halt the checks execution
            "Checks completed",
        )

        exec_command(
            capfd,
            f"-e DEFAULT_SCALE_BACKEND=55 -e ASSIGNED_MEMORY_BACKEND=1G {check}",
            "Your deployment requires 55GB of RAM but your nodes only have",
            # The error does not halt the checks execution
            "Checks completed",
        )

        exec_command(
            capfd,
            f"-e DEFAULT_SCALE_BACKEND=50 -e ASSIGNED_CPU_BACKEND=1 {check}",
            "Your deployment requires ",
            " cpus but your nodes only have ",
            # The error does not halt the checks execution
            "Checks completed",
        )
