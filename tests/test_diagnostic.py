"""
This module will test the diagnostic command
"""


from tests import create_project, exec_command


def test_diagnostic(capfd):

    create_project(
        capfd=capfd,
        name="first",
        auth="postgres",
        frontend="no",
        init=True,
        pull=False,
        start=False,
    )

    exec_command(capfd, "diagnostic http://localhost", "http schema not supported")
    exec_command(
        capfd,
        "diagnostic https://nolocalhost",
        "Host https://nolocalhost is unreachable",
    )
    exec_command(
        capfd, "diagnostic nolocalhost", "Host https://nolocalhost is unreachable"
    )
