"""
This module will test the remove command
"""
import time
from typing import List, Tuple

from python_on_whales import docker

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


def get_containers() -> List[str]:
    containers: List[str] = []

    for container in docker.container.list():
        name = container.name
        # this is swarm mode:
        # project_service.slot.id
        if "." in name:
            name = name[0 : name.index(".")]
        # this is compose mode:
        # project_service_slot
        else:
            index_of_second_underscore = name.index("_", name.index("_") + 1)
            name = name[0:index_of_second_underscore]

        # in both cases now name is:
        # project_service
        containers.append(name)

    # Return the containers sorted by name
    return sorted(containers)


def get_networks() -> List[str]:

    return [net.name for net in docker.network.list()]


def count_volumes() -> Tuple[int, int]:

    named = 0
    unnamed = 0

    for volume in docker.volume.list():
        name = volume.name
        if "_" in name:
            named += 1
        else:
            unnamed += 1

    return named, unnamed


def test_remove(capfd: Capture) -> None:

    create_project(
        capfd=capfd,
        name="rem",
        auth="postgres",
        frontend="no",
    )
    init_project(capfd)

    if SWARM_MODE:
        start_registry(capfd)

    pull_images(capfd)

    if SWARM_MODE:
        exec_command(
            capfd,
            "remove backend",
            "Stack rem is not running, deploy it with rapydo start",
        )
    else:
        exec_command(
            capfd,
            "remove",
            "Stack removed",
        )

    NONE: List[str] = []
    # BACKEND_ONLY  = ["rem_backend"]
    POSTGRES_ONLY = ["rem_postgres"]
    ALL = ["rem_backend", "rem_postgres"]

    assert get_containers() == NONE

    start_project(capfd)

    time.sleep(2)

    NAMED_VOLUMES_NUM, UNNAMED_VOLUMES_NUM = count_volumes()

    if SWARM_MODE:
        NETWORK_NAME = "rem_swarm_default"
    else:
        NETWORK_NAME = "rem_compose_default"

    assert get_containers() == ALL

    if SWARM_MODE:
        # In swarm mode remove single service is equivalent to scale 0
        exec_command(
            capfd,
            "remove backend",
            "rem_backend scaled to 0",
            "verify: Service converged",
            "Services removed",
        )

        assert get_containers() == POSTGRES_ONLY
        # Single service remove does not remove the network
        assert NETWORK_NAME in get_networks()
        # Single service remove does not remove any volume
        n, u = count_volumes()
        assert NAMED_VOLUMES_NUM == n
        assert UNNAMED_VOLUMES_NUM == u

        exec_command(
            capfd,
            "restart",
            "Stack restarted",
        )

        assert get_containers() == ALL

        exec_command(
            capfd,
            "remove",
            "Stack removed",
        )

        assert get_containers() == NONE
        # Removal of all services also drop the network
        assert NETWORK_NAME not in get_networks()
        # Removal of all services does not remove any volume
        n, u = count_volumes()
        assert NAMED_VOLUMES_NUM == n
        assert UNNAMED_VOLUMES_NUM == u
    else:

        exec_command(
            capfd,
            "remove backend",
            "Stack removed",
        )

        assert get_containers() == POSTGRES_ONLY
        # Single service remove does not remove the network
        assert NETWORK_NAME in get_networks()
        # Removal of all services does not remove any volume
        n, u = count_volumes()
        assert NAMED_VOLUMES_NUM == n
        assert UNNAMED_VOLUMES_NUM == u

        exec_command(
            capfd,
            "remove",
            "Stack removed",
        )

        assert get_containers() == NONE
        # Removal of all services also drop the network
        assert NETWORK_NAME not in get_networks()
        # Removal of all services does not remove any volume
        n, u = count_volumes()
        assert NAMED_VOLUMES_NUM == n
        assert UNNAMED_VOLUMES_NUM == u

        exec_command(
            capfd,
            "remove --all backend",
            "Stack removed",
        )

        assert get_containers() == NONE
        # Removal of all services with --all flag remove unnamed volumes
        n, u = count_volumes()
        assert NAMED_VOLUMES_NUM == n
        assert UNNAMED_VOLUMES_NUM < u

        # New counts, after single service --all has removed some unnamed volume
        NAMED_VOLUMES_NUM, UNNAMED_VOLUMES_NUM = count_volumes()

        exec_command(
            capfd, "remove --all", "--all option not implemented yet", "Stack removed"
        )

        # Removal of all services does not remove any volume because it is:
        # NOT IMPLEMENTED YET
        n, u = count_volumes()
        assert NAMED_VOLUMES_NUM == n
        assert UNNAMED_VOLUMES_NUM == u
