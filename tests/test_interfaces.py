"""
This module will test the interfaces command
"""

from tests import create_project, exec_command, random_project_name


def test_interfaces(capfd, fake):

    create_project(
        capfd=capfd,
        name=random_project_name(fake),
        auth="postgres",
        frontend="no",
        init=True,
        pull=False,
        start=False,
    )

    exec_command(capfd, "remove --all", "Stack removed")

    exec_command(
        capfd,
        "interfaces XYZ",
        "Container 'XYZui' is not defined",
        "You can use rapydo interfaces list to get available interfaces",
    )
    exec_command(
        capfd,
        "interfaces list",
        "List of available interfaces:",
        " - mongo",
        " - sqlalchemy",
        " - swagger",
        " - celery",
    )

    exec_command(
        capfd,
        "interfaces sqlalchemy --port XYZ --detach",
        "Invalid value for '--port' / '-p': XYZ is not a valid integer",
    )

    exec_command(
        capfd,
        "interfaces sqlalchemy --detach",
        "Launching interface: sqlalchemyui",
        "docker-compose command: 'run'",
    )
    exec_command(
        capfd,
        "interfaces sqlalchemy --port 123 --detach",
        "Launching interface: sqlalchemyui",
        "docker-compose command: 'run'",
    )

    exec_command(
        capfd,
        "interfaces swagger --port 124 --detach",
        "You can access swaggerui web page here:",
        "http://localhost:124?docExpansion=list&",
        "url=http://localhost:8080/api/specs",
    )

    exec_command(
        capfd,
        "--prod init -f",
        "Created default .projectrc file",
        "Project initialized",
    )

    exec_command(
        capfd,
        "--prod interfaces swagger --port 124 --detach",
        "You can access swaggerui web page here:",
        "https://localhost:124?docExpansion=list&",
        "url=https://localhost/api/specs",
    )

    exec_command(capfd, "remove --all", "Stack removed")
