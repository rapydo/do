from controller import __version__, gitter
from tests import TemporaryRemovePath, create_project, exec_command


def test_base(capfd):

    create_project(
        capfd=capfd, name="first", auth="postgres", frontend="angular", init=False
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

    with TemporaryRemovePath("projects/first/builds"):
        exec_command(
            capfd,
            "check -i main --no-git --no-builds",
            "Project first is invalid: required folder not found projects/first/builds",
        )

    with TemporaryRemovePath(".gitignore"):
        exec_command(
            capfd,
            "check -i main --no-git --no-builds",
            "Project first is invalid: required file not found .gitignore",
        )
