"""
This module will test the swarm mode
"""
import random
import shutil
import signal
import time
from datetime import datetime
from pathlib import Path

from controller.deploy.swarm import Swarm
from tests import (
    Capture,
    create_project,
    exec_command,
    mock_KeyboardInterrupt,
    pull_images,
    start_registry,
)


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
    # ################## CHECK ########################
    ###################################################

    # Skipping main because we are on a fake git repository
    exec_command(
        capfd,
        "check -i main",
        "Swarm is correctly initialized",
        "Checks completed",
    )

    swarm = Swarm()
    swarm.leave()

    exec_command(
        capfd,
        "check -i main",
        "Swarm is not initialized, please execute rapydo init",
    )
    exec_command(
        capfd,
        "init",
        "Swarm is now initialized",
        "Project initialized",
    )
    exec_command(
        capfd,
        "check -i main",
        "Swarm is correctly initialized",
        "Checks completed",
    )

    check = "check -i main --no-git --no-builds"

    exec_command(
        capfd,
        f"-e ASSIGNED_MEMORY_BACKEND=50G {check}",
        "Your deployment requires 50GB of RAM but your nodes only have",
        # The error does not halt the checks execution
        "Checks completed",
    )

    # exec_command(
    #     capfd,
    #     f"-e ASSIGNED_CPU_BACKEND=50 {check}",
    #     "Your deployment requires ",
    #     " cpus but your nodes only have ",
    #     # The error does not halt the checks execution
    #     "Checks completed",
    # )

    exec_command(
        capfd,
        f"-e DEFAULT_SCALE_BACKEND=55 -e ASSIGNED_MEMORY_BACKEND=1G {check}",
        "Your deployment requires 55GB of RAM but your nodes only have",
        # The error does not halt the checks execution
        "Checks completed",
    )

    # exec_command(
    #     capfd,
    #     f"-e DEFAULT_SCALE_BACKEND=50 -e ASSIGNED_CPU_BACKEND=1 {check}",
    #     "Your deployment requires ",
    #     " cpus but your nodes only have ",
    #     # The error does not halt the checks execution
    #     "Checks completed",
    # )

    ###################################################
    # ################### JOIN ########################
    ###################################################

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

    exec_command(
        capfd,
        "start",
        "Registry 127.0.0.1:5000 not reachable.",
    )

    start_registry(capfd)

    ###################################################
    # ################## START ########################
    ###################################################

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

    ###################################################
    # ################### LOGS ########################
    ###################################################

    exec_command(
        capfd,
        "logs invalid",
        "No such service: invalid",
    )

    # Wait for the backend startup
    time.sleep(2)

    start = datetime.now()
    signal.signal(signal.SIGALRM, mock_KeyboardInterrupt)
    signal.alarm(3)
    # Here using main services option
    exec_command(
        capfd,
        "logs --tail 10 --follow backend",
        # uhmm... nothing shown on GA ... problems with tty?
        # "*** RESTful HTTP API ***",
    )
    end = datetime.now()

    assert (end - start).seconds >= 2

    exec_command(
        capfd,
        "logs backend",
        "*** RESTful HTTP API ***",
    )

    exec_command(
        capfd,
        "logs frontend",
    )

    ###################################################
    # ############## START AGAIN ######################
    ###################################################

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
