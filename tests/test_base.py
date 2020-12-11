from controller import __version__
from tests import exec_command


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
