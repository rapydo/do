"""
This module will test the registry service
"""
import random
import time

from controller import SWARM_MODE, __version__, colors
from controller.deploy.docker import Docker
from tests import Capture, create_project, exec_command


def test_docker_registry(capfd: Capture) -> None:

    if not SWARM_MODE:
        return None

    rand = random.SystemRandom()

    auth = rand.choice(
        (
            "postgres",
            "mysql",
            "neo4j",
            "mongo",
        )
    )

    create_project(
        capfd=capfd,
        name="swarm",
        auth=auth,
        frontend="no",
        services=["rabbitmq"],
    )

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

    exec_command(
        capfd,
        "run registry",
        "Creating",
        "_registry_run",
    )

    time.sleep(1)

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
        "pull rabbitmq",
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
    )

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
    )

    exec_command(
        capfd,
        f"images --remove rapydo/rabbitmq:{__version__}",
        "This registry contains no images",
    )
