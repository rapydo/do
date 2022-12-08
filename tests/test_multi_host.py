"""
This module will test the swarm multi host mode
"""
import random

from python_on_whales import docker

from controller import colors
from controller.app import Configuration
from tests import Capture, create_project, exec_command, pull_images, start_registry


def test_swarm_multi_host(capfd: Capture) -> None:

    if not Configuration.swarm_mode:
        return None

    rand = random.SystemRandom()

    auth = rand.choice(
        (
            "postgres",
            "neo4j",
        )
    )

    create_project(
        capfd=capfd,
        name="swarm",
        auth=auth,
        frontend="no",
    )

    for node in docker.node.list():
        if node.spec.role.lower() == "manager":
            MANAGER_ADDRESS = node.status.addr

    assert MANAGER_ADDRESS is not None
    # IP=$(echo $TOKEN | awk {'print $6'} | awk -F: {'print $1'})
    # REGISTRY_HOST="${IP}:5000"
    # NFS_HOST="${IP}

    exec_command(
        capfd,
        "-e HEALTHCHECK_INTERVAL=1s init",
        "docker compose is installed",
        "NFS Server is enabled",
        # already initialized before the test, in the workflow yml
        "Swarm is already initialized",
        "Project initialized",
    )

    start_registry(capfd)
    pull_images(capfd)

    exec_command(
        capfd,
        "start backend",
        "A volume path is missing and can't be automatically created: ",
        f"Suggested command: {colors.RED}sudo mkdir -p /volumes/ssl_certs",
        "&& sudo chown ",
    )

    exec_command(
        capfd,
        "-e HEALTHCHECK_INTERVAL=1s -e NFS_EXPORTS_SSL_CERTS=/tmp/ssl_certs init -f",
    )
    # Deploy a sub-stack
    exec_command(
        capfd,
        "start backend",
        "A volume path was missing and was automatically created: /tmp/ssl_certs",
        "Stack started",
    )

    exec_command(
        capfd,
        "status",
        "Manager",
        # Still unable to add workers because GA instances lack nested virtualization
        # See details in pytests.yml (VT-x is not available)
        # "Worker",
        "Ready+Active",
        "swarm_backend",
        " [1]",
        # "running",
        # This is because NFS is not installed/configured for this test...
        # to be completed
        "error while mounting volume",
    )
