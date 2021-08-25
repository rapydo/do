"""
This module will test the swarm mode
"""
import random
import shutil
from pathlib import Path

from tests import Capture, create_project, exec_command, pull_images, start_registry


def test_swarm(capfd: Capture) -> None:

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
        capfd=capfd, name="swarm", auth=auth, frontend="angular", services=["redis"]
    )

    exec_command(
        capfd,
        "-e HEALTHCHECK_INTERVAL=1s init",
        "Swarm is now initialized",
        "Project initialized",
    )
    ###################################################
    # ################## START ########################
    ###################################################

    exec_command(
        capfd,
        "start",
        "Registry 127.0.0.1:5000 not reachable.",
    )

    start_registry(capfd)

    exec_command(
        capfd,
        "start backend invalid",
        "No such service: invalid",
    )

    exec_command(
        capfd,
        "start backend",
        "image, execute rapydo pull backend",
    )

    pull_images(capfd)

    # Deploy a sub-stack
    exec_command(
        capfd,
        "start backend",
        "Stack started",
    )

    # Once started a stack in swarm mode, it's not possible
    # to re-deploy another stack
    exec_command(
        capfd,
        "start",
        "A stack is already running",
        "Stop it with rapydo remove if you want to start a new stack",
    )

    exec_command(
        capfd,
        "remove",
    )

    # Deploy the full stack
    exec_command(
        capfd,
        "start",
        "Stack started",
    )

    # Once started a stack in swarm mode, it's not possible
    # to re-deploy another stack
    exec_command(
        capfd,
        "start backend",
        "A stack is already running",
        "Stop it with rapydo remove if you want to start a new stack",
    )

    # ############################
    # Verify bind volumes checks #
    # ############################
    data_folder = Path("data", "swarm")
    karma_folder = data_folder.joinpath("karma")

    # Delete data/swarm/karma and it will be recreated
    assert karma_folder.exists()
    shutil.rmtree(karma_folder)
    assert not karma_folder.exists()

    # set the data folder read only
    data_folder.chmod(0o550)

    # The missing folder can't be recreated due to permissions denied
    exec_command(
        capfd,
        "start frontend",
        "A bind folder is missing and can't be automatically created: ",
        "/data/swarm/karma",
    )
    assert not karma_folder.exists()

    # Restore RW permissions
    data_folder.chmod(0o770)

    exec_command(
        capfd,
        "start frontend",
        "A bind folder was missing and was automatically created: ",
        "/data/swarm/karma",
        "Stack started",
    )
    assert karma_folder.exists()
