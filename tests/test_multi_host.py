"""
This module will test the swarm multi host mode
"""
import random

from python_on_whales import docker

from tests import Capture, create_project, exec_command, start_registry


def test_swarm_multi_host(capfd: Capture) -> None:

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
        services=["rabbit", "redis"],
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
        "docker buildx is installed",
        "docker compose is installed",
        # already initialized before the test, in the workflow yml
        "Swarm is already initialized",
        "Project initialized",
    )

    start_registry(capfd)

    exec_command(
        capfd,
        "pull --quiet",
        "Base images pulled from docker hub",
    )

    # Deploy a sub-stack
    exec_command(
        capfd,
        "-s backend start",
        "Stack started",
    )

    exec_command(
        capfd,
        "status",
        "====== Nodes ======",
        "Manager",
        # Still unable to add workers because GA instances lack nested virtualization
        # See details in pytests.yml (VT-x is not available)
        # "Worker",
        "Ready+Active",
        "====== Services ======",
        "swarm_backend",
        " [1]",
        # "running",
        # This is because NFS is not installed/configured for this test...
        # to be completed
        "error while mounting volume",
    )
