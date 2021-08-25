"""
This module will test the join command
"""
from controller import SWARM_MODE
from tests import Capture, create_project, exec_command, init_project


def test_join(capfd: Capture) -> None:

    if not SWARM_MODE:
        return None

    create_project(capfd=capfd, name="myname", auth="postgres", frontend="no")
    init_project(capfd)

    exec_command(
        capfd,
        "join",
        "To add a worker to this swarm, run the following command:",
        "docker swarm join --token ",
    )

    exec_command(
        capfd,
        "join --manager",
        "To add a manager to this swarm, run the following command:",
        "docker swarm join --token ",
    )
