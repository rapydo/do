"""
This module will test the run command
"""
import time

from faker import Faker

from controller import SWARM_MODE, __version__, colors
from controller.deploy.docker import Docker
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

    # exec_command(
    #     capfd,
    #     "run --debug backend --command hostname",
    #     "backend-server",
    # )

    # exec_command(
    #     capfd,
    #     "run --debug backend --command whoami",
    #     "root",
    # )
    # exec_command(
    #     capfd,
    #     "run --debug backend -u developer --command whoami",
    #     "Please remember that users in volatile containers are not mapped on current ",
    #     "developer",
    # )
    # exec_command(
    #     capfd,
    #     "run --debug backend -u invalid --command whoami",
    #     "Error response from daemon:",
    #     "unable to find user invalid:",
    #     "no matching entries in passwd file",
    # )


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


def test_docker_registry(capfd: Capture) -> None:

    execute_outside(capfd, "run registry")
    if SWARM_MODE:
        execute_outside(capfd, "images")

    create_project(
        capfd=capfd,
        name="swarm",
        auth="no",
        frontend="no",
        services=["rabbit"],
    )

    if not SWARM_MODE:
        init_project(capfd)
        exec_command(
            capfd,
            "run registry",
            "Can't start the registry in compose mode",
        )

        return None

    exec_command(
        capfd,
        "-e HEALTHCHECK_INTERVAL=1s -e SWARM_MANAGER_ADDRESS=127.0.0.1 init",
        "Initializing Swarm with manager IP 127.0.0.1",
        "Swarm is now initialized",
        "Project initialized",
    )

    exec_command(
        capfd,
        "pull backend",
        "Registry 127.0.0.1:5000 not reachable. "
        f"You can start it with {colors.RED}rapydo run registry",
    )

    exec_command(
        capfd,
        "build backend",
        "Registry 127.0.0.1:5000 not reachable. "
        f"You can start it with {colors.RED}rapydo run registry",
    )

    exec_command(
        capfd,
        "start backend",
        "Registry 127.0.0.1:5000 not reachable. "
        f"You can start it with {colors.RED}rapydo run registry",
    )

    exec_command(
        capfd,
        "images",
        "Registry 127.0.0.1:5000 not reachable. "
        f"You can start it with {colors.RED}rapydo run registry",
    )

    exec_command(
        capfd,
        "registry",
        "Registry command is replaced by rapydo run registry",
    )

    img = f"rapydo/registry:{__version__}"
    exec_command(
        capfd,
        "run registry",
        f"Missing {img} image, add {colors.RED}--pull{colors.RESET} option",
    )

    exec_command(
        capfd,
        "run registry --pull",
        "Running registry...",
    )

    time.sleep(2)

    exec_command(
        capfd,
        "images",
        "This registry contains no images",
    )

    exec_command(
        capfd,
        "pull backend",
        "Base images pulled from docker hub and pushed into the local registry",
    )

    exec_command(
        capfd,
        "images",
        "This registry contains 1 image(s):",
        "rapydo/backend",
    )

    exec_command(
        capfd,
        "pull rabbit",
        "Base images pulled from docker hub and pushed into the local registry",
    )

    exec_command(
        capfd,
        "images",
        "This registry contains 2 image(s):",
        "rapydo/backend",
        "rapydo/rabbitmq",
    )

    exec_command(
        capfd,
        "run registry",
        "The registry is already running at 127.0.0.1:5000",
    )

    exec_command(
        capfd,
        "-e REGISTRY_PORT=5001 run registry",
        "The registry container is already existing, removing",
    )

    exec_command(
        capfd,
        "images --remove invalid",
        "Some of the images that you specified are not found in this registry",
    )

    # Copied from images.py
    docker = Docker()
    registry = docker.get_registry()
    host = f"https://{registry}"
    r = docker.send_registry_request(f"{host}/v2/_catalog")

    catalog = r.json()

    assert "repositories" in catalog
    assert "rapydo/backend" in catalog["repositories"]

    r = docker.send_registry_request(f"{host}/v2/rapydo/backend/tags/list")

    tags_list = r.json()

    assert "name" in tags_list
    assert tags_list["name"] == "rapydo/backend"
    assert "tags" in tags_list
    assert __version__ in tags_list["tags"]

    exec_command(
        capfd,
        f"images --remove rapydo/backend:{__version__}",
        f"Image rapydo/backend:{__version__} deleted from ",
        "Executing registry garbage collector...",
        "Registry garbage collector successfully executed",
        "Registry restarted to clean the layers cache",
    )

    time.sleep(1)

    r = docker.send_registry_request(f"{host}/v2/_catalog")

    catalog = r.json()

    assert "repositories" in catalog
    # After the delete the repository is still in the catalog but with no tag associated
    assert "rapydo/backend" in catalog["repositories"]

    r = docker.send_registry_request(f"{host}/v2/rapydo/backend/tags/list")

    tags_list = r.json()

    assert "name" in tags_list
    assert tags_list["name"] == "rapydo/backend"
    assert "tags" in tags_list
    # No tags associated to this repository
    assert tags_list["tags"] is None

    exec_command(
        capfd,
        f"images --remove rapydo/backend:{__version__}",
        "Some of the images that you specified are not found in this registry",
    )

    exec_command(
        capfd,
        "images",
        "This registry contains 1 image(s):",
        "rapydo/rabbitmq",
    )

    exec_command(
        capfd,
        f"images --remove rapydo/backend:{__version__}",
        "Some of the images that you specified are not found in this registry",
    )

    exec_command(
        capfd,
        f"images --remove rapydo/rabbitmq:{__version__}",
        f"Image rapydo/rabbitmq:{__version__} deleted from ",
        "Executing registry garbage collector...",
        "Registry garbage collector successfully executed",
        "Registry restarted to clean the layers cache",
    )

    exec_command(
        capfd,
        f"images --remove rapydo/rabbitmq:{__version__}",
        "This registry contains no images",
    )
