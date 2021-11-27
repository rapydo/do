"""
This module will test the update command
"""
from tests import Capture, create_project, exec_command, execute_outside, init_project


def test_base(capfd: Capture) -> None:

    execute_outside(capfd, "update")

    create_project(
        capfd=capfd,
        name="third",
        auth="postgres",
        frontend="angular",
    )
    init_project(capfd)

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
