"""
This module will test the swarm mode
"""
import random
import time

from controller.deploy.swarm import Swarm
from tests import Capture, create_project, exec_command


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
        capfd=capfd,
        name="swarm",
        auth=auth,
        frontend="angular",
    )

    exec_command(
        capfd,
        "-e HEALTHCHECK_INTERVAL=1s init",
        "Compose configuration dumped on docker-compose.yml",
        "Swarm is now initialized",
        "Project initialized",
    )

    exec_command(
        capfd,
        "init",
        "Compose configuration dumped on docker-compose.yml",
        "Swarm is already initialized",
        "Project initialized",
    )

    # Skipping main because we are on a fake git repository
    exec_command(
        capfd,
        "check -i main",
        "Compose configuration dumped on docker-compose.yml",
        "Swarm is correctly initialized",
        "Checks completed",
    )

    # Skipping main because we are on a fake git repository
    exec_command(
        capfd,
        "check -i main",
        "Compose configuration dumped on docker-compose.yml",
        "Swarm is correctly initialized",
        "Checks completed",
    )

    swarm = Swarm()
    swarm.leave()

    exec_command(
        capfd,
        "check -i main",
        "Compose configuration dumped on docker-compose.yml",
        "Swarm is not initialized, please execute rapydo init",
    )
    exec_command(
        capfd,
        "init",
        "Compose configuration dumped on docker-compose.yml",
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

    exec_command(
        capfd,
        f"-e ASSIGNED_CPU_BACKEND=50 {check}",
        "Your deployment requires ",
        " cpus but your nodes only have ",
        # The error does not halt the checks execution
        "Checks completed",
    )

    exec_command(
        capfd,
        f"-e DEFAULT_SCALE_BACKEND=55 -e ASSIGNED_MEMORY_BACKEND=1G {check}",
        "Your deployment requires 55GB of RAM but your nodes only have",
        # The error does not halt the checks execution
        "Checks completed",
    )

    exec_command(
        capfd,
        f"-e DEFAULT_SCALE_BACKEND=50 -e ASSIGNED_CPU_BACKEND=1 {check}",
        "Your deployment requires ",
        " cpus but your nodes only have ",
        # The error does not halt the checks execution
        "Checks completed",
    )

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
        "-s backend start",
        "image for backend service, execute rapydo pull",
    )

    exec_command(
        capfd,
        "pull --quiet",
        "Base images pulled from docker hub",
    )

    exec_command(
        capfd,
        "start --force",
        "Force flag is not yet implemented",
        "Stack started",
    )

    time.sleep(2)

    exec_command(
        capfd,
        "status",
        "====== Nodes ======",
        "Manager",
        "Ready+Active",
        "====== Services ======",
        "swarm_backend",
        "swarm_frontend",
        " [1]",
        "running",
    )

    exec_command(capfd, "shell invalid", "Service invalid not found")

    exec_command(
        capfd,
        "shell backend",
        "Due to limitations of the underlying packages, "
        "the shell command is not yet implemented",
        "You can execute by yourself the following command",
        "docker exec --interactive --tty --user developer swarm_backend.1.",
        "bash",
    )

    exec_command(
        capfd,
        "shell backend --default",
        "Due to limitations of the underlying packages, "
        "the shell command is not yet implemented",
        "You can execute by yourself the following command",
        "docker exec --interactive --tty --user developer swarm_backend.1.",
        "restapi launch",
    )

    exec_command(capfd, "shell backend -u aRandomUser", "--user aRandomUser")

    exec_command(
        capfd,
        "-s invalid logs",
        "No such service: invalid",
    )

    exec_command(
        capfd,
        "-s backend,frontend logs",
        "Due to limitations of the underlying packages, the logs command "
        "is only supported for single services",
    )

    exec_command(
        capfd,
        "-s backend logs --follow",
        "Due to limitations of the underlying packages, the logs command "
        "does not support the --follow flag yet",
    )

    time.sleep(2)

    exec_command(
        capfd,
        "-s backend logs",
        "*** RESTful HTTP API ***",
        "Due to limitations of the underlying packages, the logs command "
        "only prints stdout, stderr is ignored",
    )

    exec_command(
        capfd, "scale backend=2", "swarm_backend scaled to 2", "Service converged"
    )

    exec_command(
        capfd,
        "status",
        " [2]",
    )

    exec_command(
        capfd,
        "-e DEFAULT_SCALE_BACKEND=3 scale backend",
        "swarm_backend scaled to 3",
        "Service converged",
    )

    exec_command(
        capfd,
        "status",
        " [3]",
    )

    exec_command(
        capfd,
        "scale backend=x",
        "Invalid number of replicas: x",
    )

    with open(".projectrc", "a") as f:
        f.write("\n      DEFAULT_SCALE_BACKEND: 4\n")

    exec_command(
        capfd, "scale backend", "swarm_backend scaled to 4", "Service converged"
    )

    exec_command(
        capfd, "scale backend=0", "swarm_backend scaled to 0", "Service converged"
    )

    time.sleep(2)

    exec_command(
        capfd,
        "status",
        "! no task is running",
    )

    exec_command(
        capfd,
        "stop",
        "Stop command is not implemented in Swarm Mode",
        "Stop is in contrast with the Docker Swarm approach",
        "You can remove the stack => rapydo remove",
        "Or you can scale all the services to zero => rapydo scale service=0",
    )

    exec_command(
        capfd, "remove --all", "rm_all flag is not implemented yet", "Not implemented"
    )

    exec_command(
        capfd, "remove", "rm_networks is currently always enabled", "Stack removed"
    )

    time.sleep(2)

    exec_command(
        capfd,
        "status",
        "====== Nodes ======",
        "Manager",
        "Ready+Active",
        "No service is running",
    )
