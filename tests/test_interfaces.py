"""
This module will test the interfaces command
"""
from faker import Faker

from tests import (
    Capture,
    create_project,
    exec_command,
    init_project,
    random_project_name,
)


def test_interfaces(capfd: Capture, faker: Faker) -> None:

    create_project(
        capfd=capfd,
        name=random_project_name(faker),
        auth="postgres",
        frontend="no",
    )
    init_project(capfd)

    exec_command(
        capfd,
        "interfaces sqlalchemy",
        "Deprecated interface sqlalchemy, use adminer instead",
    )

    exec_command(
        capfd,
        "interfaces adminer",
        "Interfaces command is replaced by rapydo run adminer",
    )

    exec_command(
        capfd,
        "run adminer --port XYZ",
        "Invalid value for '--port' / '-p': XYZ is not a valid integer",
    )

    exec_command(
        capfd,
        "run adminer",
        "Launching interface: adminer",
        "docker-compose command: 'run'",
    )
    exec_command(
        capfd,
        "run adminer --port 123",
        "Launching interface: adminer",
        "docker-compose command: 'run'",
    )

    exec_command(
        capfd,
        "run swaggerui --port 124",
        "You can access SwaggerUI web page here: http://localhost:124",
    )

    exec_command(
        capfd,
        "--prod init -f",
        "Created default .projectrc file",
        "Project initialized",
    )

    exec_command(
        capfd,
        "--prod run swaggerui --port 124",
        "You can access SwaggerUI web page here: https://localhost:124",
    )
