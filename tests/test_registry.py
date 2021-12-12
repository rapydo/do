"""
This module will test the run registry and image commands
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
    random_project_name,
)


def test_docker_registry(capfd: Capture, faker: Faker) -> None:

    execute_outside(capfd, "run registry")
    if SWARM_MODE:
        execute_outside(capfd, "images")

    create_project(
        capfd=capfd,
        name=random_project_name(faker),
        auth="no",
        frontend="no",
        services=["rabbit"],
    )
    init_project(capfd)

    if not SWARM_MODE:
        exec_command(
            capfd,
            "run registry",
            "Can't start the registry in compose mode",
        )

        return None

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
    registry = docker.registry.get_host()
    host = f"https://{registry}"
    r = docker.registry.send_request(f"{host}/v2/_catalog")

    catalog = r.json()

    assert "repositories" in catalog
    assert "rapydo/backend" in catalog["repositories"]

    r = docker.registry.send_request(f"{host}/v2/rapydo/backend/tags/list")

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

    r = docker.registry.send_request(f"{host}/v2/_catalog")

    catalog = r.json()

    assert "repositories" in catalog
    # After the delete the repository is still in the catalog but with no tag associated
    assert "rapydo/backend" in catalog["repositories"]

    r = docker.registry.send_request(f"{host}/v2/rapydo/backend/tags/list")

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
