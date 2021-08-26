"""
This module will test the interfaces command
"""
from faker import Faker

from controller import SWARM_MODE, __version__
from tests import (
    Capture,
    create_project,
    exec_command,
    init_project,
    random_project_name,
    start_registry,
)


def test_interfaces(capfd: Capture, faker: Faker) -> None:
    project_name = random_project_name(faker)
    create_project(
        capfd=capfd,
        name=project_name,
        auth="postgres",
        frontend="no",
    )
    init_project(capfd)

    if SWARM_MODE:
        start_registry(capfd)

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
        f"Missing rapydo/adminer:{__version__} image, add --pull option",
    )

    # Launch Adminer UI with default port
    exec_command(
        capfd,
        "run adminer --pull",
        # "Pulling adminer",
        # f"Creating {project_name}_adminer_run",
        "You can access Adminer interface on: http://localhost:7777",
    )

    # Launch Adminer UI with custom port
    exec_command(
        capfd,
        "run adminer --port 123",
        # "Pulling adminer",
        # f"Creating {project_name}_adminer_run",
        "You can access Adminer interface on: http://localhost:123",
    )

    # Launch Swagger UI with default port
    exec_command(
        capfd,
        "run swaggerui --pull",
        "You can access SwaggerUI web page here: http://localhost:7777",
    )

    # Launch Swagger UI with custom port
    exec_command(
        capfd,
        "run swaggerui --port 124",
        "You can access SwaggerUI web page here: http://localhost:124",
    )

    # Test Swagger UI and Admin in production mode
    exec_command(
        capfd,
        "--prod init -f",
        "Created default .projectrc file",
        "Project initialized",
    )

    exec_command(
        capfd,
        "--prod run swaggerui --port 125",
        "You can access SwaggerUI web page here: https://localhost:125",
    )

    exec_command(
        capfd,
        "--prod run adminer --port 126",
        "You can access Adminer interface on: https://localhost:126",
    )
