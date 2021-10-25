"""
This module will test the interfaces command
"""
from faker import Faker

from controller import __version__, colors
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
        "Invalid value for '--port' / '-p': 'XYZ' is not a valid integer",
    )

    exec_command(
        capfd,
        "run adminer",
        f"Missing rapydo/adminer:{__version__} image, add {colors.RED}--pull{colors.RESET} option",
    )

    # Launch Adminer UI with default port
    exec_command(
        capfd,
        "run adminer --pull",
        "Pulling image for adminer...",
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
        "Pulling image for swaggerui...",
        "You can access SwaggerUI web page here: http://localhost:7777",
    )

    # Launch Swagger UI with custom port
    exec_command(
        capfd,
        "run swaggerui --port 124",
        "You can access SwaggerUI web page here: http://localhost:124",
    )

    # This fails if the interfaces are non running, i.e. in case of a post-start crash
    # Introduced after a BUG due to the tty setting in volatile container
    # that made run interfaces fail on GA
    exec_command(
        capfd,
        "remove adminer swaggerui",
        "Service adminer removed",
        "Service swaggerui removed",
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
