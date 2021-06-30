"""
This module will test the scale command
"""
import os

from tests import Capture, create_project, exec_command, init_project, pull_images


def test_scale(capfd: Capture) -> None:

    create_project(
        capfd=capfd,
        name="first",
        auth="postgres",
        frontend="angular",
        services=["rabbit"],
    )
    init_project(capfd)

    exec_command(
        capfd,
        "scale rabbit=2",
        "image for rabbit service, execute rapydo pull",
    )

    pull_images(capfd)

    exec_command(
        capfd,
        "scale rabbit",
        "Please specify how to scale: SERVICE=NUM_REPLICA",
        "You can also set a DEFAULT_SCALE_RABBIT variable in your .projectrc file",
    )
    exec_command(
        capfd,
        "-e DEFAULT_SCALE_RABBIT=2 scale rabbit",
        # "Starting first_rabbit_1",
        # "Creating first_rabbit_2",
    )
    exec_command(
        capfd,
        "scale rabbit=x",
        "Invalid number of replicas: x",
    )

    exec_command(
        capfd,
        "scale rabbit=2",
        # "Starting first_rabbit_1",
        # "Starting first_rabbit_2",
    )

    with open(".projectrc", "a") as f:
        f.write("\n      DEFAULT_SCALE_RABBIT: 3\n")

    exec_command(
        capfd,
        "scale rabbit",
        # "Starting first_rabbit_1",
        # "Starting first_rabbit_2",
        # "Creating first_rabbit_3",
    )

    exec_command(
        capfd,
        "scale rabbit=1",
        # "Starting first_rabbit_1",
        # "Stopping and removing first_rabbit_2",
        # "Stopping and removing first_rabbit_3",
    )

    # We modified projectrc to contain: DEFAULT_SCALE_RABBIT: 3
    with open(".env") as env:
        content = [line.rstrip("\n") for line in env]
    assert "DEFAULT_SCALE_RABBIT=3" in content

    # Now we set an env varable to change this value:
    os.environ["DEFAULT_SCALE_RABBIT"] = "2"
    exec_command(capfd, "check -i main")
    with open(".env") as env:
        content = [line.rstrip("\n") for line in env]
    assert "DEFAULT_SCALE_RABBIT=3" not in content
    assert "DEFAULT_SCALE_RABBIT=2" in content

    exec_command(capfd, "remove --all", "Stack removed")
