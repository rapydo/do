"""
This module will test the list command
"""

from tests import create_project, exec_command, random_project_name


def test_all(capfd, fake):

    create_project(
        capfd=capfd,
        name=random_project_name(fake),
        auth="postgres",
        frontend="angular",
        services=["rabbit", "neo4j"],
        extra="--env CUSTOMVAR1=mycustomvalue --env CUSTOMVAR2=mycustomvalue",
        init=True,
        pull=False,
        start=False,
    )

    # Some tests with list
    exec_command(
        capfd,
        "list",
        "Missing argument 'ELEMENT_TYPE:[env|services|submodules]'.  Choose from:",
    )
    exec_command(
        capfd,
        "list env",
        "List env variables:",
        "ACTIVATE_ALCHEMY",
        "CUSTOMVAR1",
        "CUSTOMVAR2",
        "mycustomvalue",
    )
    exec_command(
        capfd,
        "list submodules",
        "List of submodules:",
    )

    exec_command(
        capfd,
        "list services",
        "List of active services:",
        "backend",
        "frontend",
        "postgres",
        "rabbit",
    )

    exec_command(
        capfd,
        "list invalid",
        "Invalid value for 'ELEMENT_TYPE:[env|services|submodules]': ",
        "invalid choice: invalid. (choose from env, services, submodules)",
    )
