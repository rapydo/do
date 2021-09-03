"""
This module will test the scale command
"""
import time

from python_on_whales import docker

from controller import SWARM_MODE, colors
from tests import (
    Capture,
    create_project,
    exec_command,
    init_project,
    pull_images,
    start_project,
    start_registry,
)


def test_scale(capfd: Capture) -> None:

    create_project(
        capfd=capfd,
        name="first",
        auth="postgres",
        frontend="no",
        services=["redis"],
    )
    init_project(capfd)

    # backend, postgres, redis
    BASE_SERVICE_NUM = 3

    if SWARM_MODE:

        exec_command(
            capfd,
            "scale backend=2",
            "Registry 127.0.0.1:5000 not reachable.",
        )

        start_registry(capfd)

        # Add the registry
        BASE_SERVICE_NUM += 1

    exec_command(
        capfd,
        "scale backend=2",
        f"image, execute {colors.RED}rapydo pull backend",
    )

    pull_images(capfd)

    if SWARM_MODE:
        exec_command(
            capfd,
            "scale backend=2",
            "No such service: first_backend, have you started your stack?",
        )

    start_project(capfd)
    # Wait for the backend startup
    time.sleep(2)

    assert len(docker.container.list()) == BASE_SERVICE_NUM

    exec_command(
        capfd,
        "scale redis=x",
        "Invalid number of replicas: x",
    )

    if SWARM_MODE:

        exec_command(
            capfd,
            "scale backend=2 --wait",
            "first_backend scaled to 2",
            "Service converged",
        )

        assert len(docker.container.list()) == BASE_SERVICE_NUM + 1

        exec_command(
            capfd,
            "status",
            " [2]",
        )

        exec_command(
            capfd,
            "scale backend",
            "first_backend scaled to 1",
        )

        assert len(docker.container.list()) == BASE_SERVICE_NUM

        exec_command(
            capfd,
            "-e DEFAULT_SCALE_BACKEND=3 scale backend --wait",
            "first_backend scaled to 3",
            "Service converged",
        )

        assert len(docker.container.list()) == BASE_SERVICE_NUM + 2

        exec_command(
            capfd,
            "status",
            " [3]",
        )

        with open(".projectrc", "a") as f:
            f.write("\n      DEFAULT_SCALE_BACKEND: 4\n")

        exec_command(
            capfd,
            "scale backend",
            "first_backend scaled to 4",
        )

        assert len(docker.container.list()) == BASE_SERVICE_NUM + 3

        exec_command(
            capfd,
            "scale backend=0 --wait",
            "first_backend scaled to 0",
        )

        assert len(docker.container.list()) == BASE_SERVICE_NUM - 1

        exec_command(
            capfd,
            "scale redis=2",
            "Service redis is not guaranteed to support the scale, "
            "can't accept the request",
        )

    else:

        exec_command(
            capfd,
            "scale redis",
            "Scaling services: redis=1...",
            "Services scaled: redis=1",
        )

        assert len(docker.container.list()) == BASE_SERVICE_NUM

        exec_command(
            capfd,
            "-e DEFAULT_SCALE_REDIS=2 scale redis",
            "Scaling services: redis=2...",
            "Services scaled: redis=2",
        )

        assert len(docker.container.list()) == BASE_SERVICE_NUM + 1

        exec_command(
            capfd,
            "scale redis=3",
            "Scaling services: redis=3...",
            "Services scaled: redis=3",
        )

        assert len(docker.container.list()) == BASE_SERVICE_NUM + 2

        with open(".projectrc", "a") as f:
            f.write("\n      DEFAULT_SCALE_REDIS: 4\n")

        exec_command(
            capfd,
            "scale redis",
            "Scaling services: redis=4...",
            "Services scaled: redis=4",
        )

        assert len(docker.container.list()) == BASE_SERVICE_NUM + 3

        # This should fail due to a go panic error
        exec_command(
            capfd,
            "scale redis=1",
            "Scaling services: redis=1...",
            "Services scaled: redis=1",
        )

        assert len(docker.container.list()) == BASE_SERVICE_NUM

        exec_command(
            capfd,
            "scale redis=2",
            "Scaling services: redis=2...",
            "Services scaled: redis=2",
        )

        assert len(docker.container.list()) == BASE_SERVICE_NUM + 1

        # This should restart all the replicas.
        # Actually fails due to the panic above
        exec_command(
            capfd,
            "restart",
        )

        exec_command(
            capfd,
            "restart --force",
        )

        # Verify that 2 replicas are still running after the restat
        exec_command(
            capfd,
            "restart --force",
        )

        exec_command(
            capfd,
            "status",
            "first_redis_1",
            "first_redis_2",
        )
