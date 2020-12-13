"""
This module will test combinations of init, check and update commands.
Other module that will initialize projects will consider the init command fully working
"""
import os
import shutil

from controller import __version__, gitter
from tests import TemporaryRemovePath, create_project, exec_command


def test_base(capfd):

    create_project(
        capfd=capfd,
        name="third",
        auth="postgres",
        frontend="angular",
        init=False,
        pull=False,
        start=False,
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

    r = gitter.get_repo("submodules/http-api")
    gitter.switch_branch(r, "0.7.6")
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

    with TemporaryRemovePath("data"):
        exec_command(
            capfd,
            "check -i main --no-git --no-builds",
            "Folder not found: data",
            "Please note that this command only works from inside a rapydo-like repo",
            "Verify that you are in the right folder, now you are in: ",
        )

    with TemporaryRemovePath("projects/third/builds"):
        exec_command(
            capfd,
            "check -i main --no-git --no-builds",
            "Project third is invalid: required folder not found projects/third/builds",
        )

    with TemporaryRemovePath(".gitignore"):
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
    )
    os.remove("submodules/do/temp.file")
    r = gitter.get_repo("submodules/do")
    r.git().execute(["git", "checkout", "--", "setup.py"])

    # Skipping main because we are on a fake git repository
    exec_command(
        capfd,
        "check -i main",
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

    with TemporaryRemovePath("submodules.bak/do"):
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
        init=False,
        pull=False,
        start=False,
    )

    os.remove(".projectrc")

    exec_command(
        capfd,
        "check -i main --no-git --no-builds",
        "Multiple projects found, please use --project to specify one of the following",
    )

    # Test with zero projects
    with TemporaryRemovePath("projects"):
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

    # Check invalid and reserved project names
    os.makedirs("projects/invalid_character")
    exec_command(
        capfd,
        "-p invalid_character check -i main --no-git --no-builds",
        "Wrong project name, _ is not a valid character.",
    )
    shutil.rmtree("projects/invalid_character")

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

    with open(".pre-commit-config.yaml", "a") as a_file:
        a_file.write("\n")
        a_file.write("# new line")

    exec_command(
        capfd,
        "check -i main",
        ".pre-commit-config.yaml changed, "
        "please execute rapydo upgrade --path .pre-commit-config.yaml",
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
        "--prod check -i main --no-git --no-builds",
        "Checks completed",
    )
    exec_command(capfd, "remove --all", "Stack removed")
