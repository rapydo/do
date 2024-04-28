"""
This module will test the join command
"""

from controller.app import Application, Configuration
from tests import Capture, create_project, exec_command, execute_outside, init_project


def test_join(capfd: Capture) -> None:
    # load variables and initialize the Configuration
    Application()

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
