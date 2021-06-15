import typer
from python_on_whales import docker

from controller import log
from controller.app import Application
from controller.swarm import Swarm


@Application.app.command(help="Provide instructions to join new nodes")
def join(
    manager: bool = typer.Option(
        False, "--manager", show_default=False, help="join new node with manager role"
    )
) -> None:
    Application.get_controller().controller_init()

    swarm = Swarm()

    manager_address = "N/A"
    # Search for the manager address
    for node in docker.node.list():

        role = node.spec.role
        state = node.status.state
        availability = node.spec.availability

        if role == "manager" and state == "ready" and availability == "active":
            manager_address = node.manager_status.addr

    if manager:
        log.info("To add a manager to this swarm, run the following command:")
        token = swarm.get_token("manager")
    else:
        log.info("To add a worker to this swarm, run the following command:")
        token = swarm.get_token("worker")

    print("")
    print(f"docker swarm join --token {token} {manager_address}")
    print("")