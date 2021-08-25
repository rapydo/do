"""
This module will test the scale command
"""
import os
import time

from controller import SWARM_MODE
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
        services=["rabbit", "redis"],
    )
    init_project(capfd)

    if SWARM_MODE:

        exec_command(
            capfd,
            "scale backend=2",
            "Registry 127.0.0.1:5000 not reachable.",
        )

        start_registry(capfd)

    exec_command(
        capfd,
        "scale backend=2",
        "image, execute rapydo pull backend",
    )

    pull_images(capfd)

    if SWARM_MODE:
        exec_command(
            capfd,
            "scale backend=2",
            "No such service: swarm_backend, have you started your stack?",
        )

    start_project(capfd)
    # Wait for the backend startup
    time.sleep(2)

    exec_command(
        capfd,
        "scale rabbit=x",
        "Invalid number of replicas: x",
    )

    if SWARM_MODE:

        exec_command(
            capfd,
            "scale backend=2 --wait",
            "swarm_backend scaled to 2",
            "Service converged",
        )

        exec_command(
            capfd,
            "status",
            " [2]",
        )

        exec_command(
            capfd,
            "scale backend",
            "swarm_backend scaled to 1",
        )

        exec_command(
            capfd,
            "-e DEFAULT_SCALE_BACKEND=3 scale backend --wait",
            "swarm_backend scaled to 3",
            "Service converged",
        )

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
            "swarm_backend scaled to 4",
        )

        exec_command(
            capfd,
            "scale backend=0 --wait",
            "swarm_backend scaled to 0",
        )

        exec_command(
            capfd,
            "scale redis=2",
            "Service redis is not guaranteed to support the scale, "
            "can't accept the request",
        )

    else:

        exec_command(
            capfd,
            "scale rabbit",
        )
        exec_command(
            capfd,
            "-e DEFAULT_SCALE_RABBIT=2 scale rabbit",
        )

        exec_command(
            capfd,
            "scale rabbit=2",
        )

        with open(".projectrc", "a") as f:
            f.write("\n      DEFAULT_SCALE_RABBIT: 3\n")

        exec_command(
            capfd,
            "scale rabbit",
        )

        exec_command(
            capfd,
            "scale rabbit=1",
        )

    # We modified projectrc to contain: DEFAULT_SCALE_RABBIT: 3
    with open(".env") as env:
        content = [line.rstrip("\n") for line in env]
    assert "DEFAULT_SCALE_RABBIT=3" in content

    # Now we set an env variable to change this value:
    os.environ["DEFAULT_SCALE_RABBIT"] = "2"
    exec_command(capfd, "check -i main")
    with open(".env") as env:
        content = [line.rstrip("\n") for line in env]
    assert "DEFAULT_SCALE_RABBIT=3" not in content
    assert "DEFAULT_SCALE_RABBIT=2" in content

    exec_command(capfd, "remove", "Stack removed")
