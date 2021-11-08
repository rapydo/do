"""
This module will test the run command
"""

from faker import Faker

from controller import __version__, colors
from tests import (
    Capture,
    create_project,
    exec_command,
    execute_outside,
    init_project,
    pull_images,
    random_project_name,
    start_registry,
)


def test_debug_run(capfd: Capture, faker: Faker) -> None:

    execute_outside(capfd, "run backend")

    create_project(
        capfd=capfd,
        name=random_project_name(faker),
        auth="no",
        frontend="no",
    )
    init_project(capfd)

    start_registry(capfd)

    exec_command(
        capfd,
        "volatile backend",
        "Volatile command is replaced by rapydo run --debug backend",
    )

    img = f"rapydo/backend:{__version__}"
    exec_command(
        capfd,
        "run --debug backend",
        f"Missing {img} image, add {colors.RED}--pull{colors.RESET} option",
    )

    pull_images(capfd)
    # start_project(capfd)

    # exec_command(
    #     capfd,
    #     "run --debug backend --command hostname",
    #     "Bind for 0.0.0.0:8080 failed: port is already allocated",
    # )

    # exec_command(
    #     capfd,
    #     "remove",
    #     "Stack removed",
    # )

    exec_command(
        capfd,
        "run backend --command hostname",
        "Can't specify a command if debug mode is OFF",
    )

    exec_command(
        capfd,
        "run backend --command hostname --user developer",
        "Can't specify a user if debug mode is OFF",
    )

    # TEMPORARY DISABLED REF736
    # exec_command(
    #     capfd,
    #     "run --debug backend --command hostname",
    #     "backend-server",
    # )

    # TEMPORARY DISABLED REF736
    # exec_command(
    #     capfd,
    #     "run --debug backend --command whoami",
    #     "root",
    # )

    # TEMPORARY DISABLED REF736
    # exec_command(
    #     capfd,
    #     "run --debug backend -u developer --command whoami",
    #     "Please remember that users in volatile containers are not mapped on current ",
    #     "developer",
    # )

    # TEMPORARY DISABLED REF736
    # exec_command(
    #     capfd,
    #     "run --debug backend -u invalid --command whoami",
    #     "Error response from daemon:",
    #     "unable to find user invalid:",
    #     "no matching entries in passwd file",
    # )


def test_interfaces(capfd: Capture, faker: Faker) -> None:

    execute_outside(capfd, "run adminer")

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

    img = f"rapydo/adminer:{__version__}"
    exec_command(
        capfd,
        "run adminer",
        f"Missing {img} image, add {colors.RED}--pull{colors.RESET} option",
    )

    # Launch Adminer UI with default port
    exec_command(
        capfd,
        "run adminer --pull --detach",
        "Pulling image for adminer...",
        # f"Creating {project_name}_adminer_run",
        "You can access Adminer interface on: http://localhost:7777",
    )

    # Admin or SwaggerUI does not start? You can debug with:
    # from python_on_whales import docker
    # assert docker.logs("adminer", tail=10) == "debug"

    exec_command(
        capfd,
        "remove adminer",
        "Service adminer removed",
    )

    # Launch Adminer UI with custom port
    exec_command(
        capfd,
        "run adminer --port 3333 --detach",
        # "Pulling adminer",
        # f"Creating {project_name}_adminer_run",
        "You can access Adminer interface on: http://localhost:3333",
    )

    # Launch Swagger UI with default port
    exec_command(
        capfd,
        "run swaggerui --pull --detach",
        "Pulling image for swaggerui...",
        "You can access SwaggerUI web page here: http://localhost:7777",
    )

    exec_command(
        capfd,
        "remove swaggerui",
        "Service swaggerui removed",
    )

    # Launch Swagger UI with custom port
    exec_command(
        capfd,
        "run swaggerui --port 4444 --detach",
        "You can access SwaggerUI web page here: http://localhost:4444",
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
        "--prod run swaggerui --port 5555 --detach",
        "You can access SwaggerUI web page here: https://localhost:5555",
    )

    exec_command(
        capfd,
        "--prod run adminer --port 6666 --detach",
        "You can access Adminer interface on: https://localhost:6666",
    )

    # Problems with the certificate?
    # Service adminer is not running
    # Service swaggerui is not running
    # exec_command(
    #     capfd,
    #     "remove adminer swaggerui",
    #     "Service adminer removed",
    #     "Service swaggerui removed",
    # )
