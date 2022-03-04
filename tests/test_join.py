"""
This module will test the join command
"""
from controller.app import Configuration
from tests import Capture, create_project, exec_command, execute_outside, init_project


def test_join(capfd: Capture) -> None:

    if not Configuration.swarm_mode:
        return None

    execute_outside(capfd, "join")

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
