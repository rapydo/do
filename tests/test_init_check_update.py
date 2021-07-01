"""
This module will test combinations of init, check and update commands.
Other module that will initialize projects will consider the init command fully working
"""
import os
import shutil
from pathlib import Path

from controller import __version__
from controller.utilities import git
from tests import Capture, TemporaryRemovePath, create_project, exec_command


def test_base(capfd: Capture) -> None:

    create_project(
        capfd=capfd,
        name="third",
        auth="postgres",
        frontend="angular",
    )

    # Basic initialization
    exec_command(
        capfd,
        "check -i main",
        "Repo https://github.com/rapydo/http-api.git missing as submodules/http-api.",
        "You should init your project",
    )
    exec_command(
        capfd,
        "init",
        "Project initialized",
    )

    r = git.get_repo("submodules/http-api")
    git.switch_branch(r, "0.7.6")
    exec_command(
        capfd,
        "check -i main",
        f"http-api: wrong branch 0.7.6, expected {__version__}",
        "You can use rapydo init to fix it",
    )
    exec_command(
        capfd,
        "init",
        f"Switched http-api branch from 0.7.6 to {__version__}",
        f"build-templates already set on branch {__version__}",
        f"do already set on branch {__version__}",
    )

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

    # Skipping main because we are on a fake git repository
    exec_command(
        capfd,
        "update -i main",
        "All updated",
    )

    open("submodules/do/temp.file", "a").close()
    with open("submodules/do/setup.py", "a") as f:
        f.write("# added from tests\n")

    exec_command(
        capfd,
        "update -i main",
        "Unable to update do repo, you have unstaged files",
        "Untracked files:",
        "submodules/do/temp.file",
        "Changes not staged for commit:",
        "submodules/do/setup.py",
        "Can't continue with updates",
    )
    os.remove("submodules/do/temp.file")
    r = git.get_repo("submodules/do")
    r.git().execute(["git", "checkout", "--", "setup.py"])

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
        " image, execute rapydo pull",
        " image, execute rapydo build",
        "Checks completed",
    )

    exec_command(
        capfd,
        "--stack invalid check -i main",
        "Failed to read projects/third/confs/invalid.yml: File does not exist",
    )

    os.rename("submodules", "submodules.bak")
    os.mkdir("submodules")

    # This is to re-fill the submodules folder,
    # these folder will be removed by the next init
    exec_command(capfd, "init", "Project initialized")

    modules_path = os.path.abspath("submodules.bak")

    with TemporaryRemovePath(Path("submodules.bak/do")):
        exec_command(
            capfd,
            f"init --submodules-path {modules_path}",
            "Submodule do not found in ",
        )
    exec_command(
        capfd,
        f"init --submodules-path {modules_path}",
        "Path submodules/http-api already exists, removing",
        "Project initialized",
    )

    assert os.path.islink("submodules/do")
    assert not os.path.islink("submodules.bak/do")

    # Init again, this time in submodules there are links...
    # and will be removed as well as the folders
    exec_command(
        capfd,
        f"init --submodules-path {modules_path}",
        "Path submodules/http-api already exists, removing",
        "Project initialized",
    )

    exec_command(
        capfd,
        "init --submodules-path invalid/path",
        "Local path not found: invalid/path",
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
    exec_command(
        capfd,
        "--project third init",
        "Project initialized",
    )
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
        "please execute rapydo upgrade --path .gitattributes",
    )

    exec_command(
        capfd,
        "--prod check -i main --no-git --no-builds",
        "The following variables are missing in your configuration",
    )

    exec_command(
        capfd,
        "--prod init -f",
        "Created default .projectrc file",
        "Project initialized",
    )

    exec_command(
        capfd,
        "--prod -e MYVAR=MYVAL init -f",
        "Created default .projectrc file",
        "Project initialized",
    )

    with open(".projectrc") as projectrc:
        lines = [line.strip() for line in projectrc.readlines()]
        assert "MYVAR: MYVAL" in lines

    exec_command(
        capfd,
        "--prod check -i main --no-git --no-builds",
        "Checks completed",
    )
    exec_command(capfd, "remove --all", "Stack removed")
