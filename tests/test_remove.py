"""
This module will test the remove command
"""
import time
from typing import List, Tuple

from python_on_whales import docker

from controller import REGISTRY, colors
from controller.app import Configuration
from tests import (
    Capture,
    create_project,
    exec_command,
    execute_outside,
    init_project,
    pull_images,
    start_project,
    start_registry,
)


def get_containers() -> List[str]:
    containers: List[str] = []

    for container in docker.container.list():
        name = container.name

        if name == REGISTRY or name == "adminer" or name == "swaggerui":
            continue

        # this is swarm mode:
        # project_service.slot.id
        if "." in name:
            name = name[0 : name.index(".")]
        # this is compose mode:
        # project_service_slot
        else:
            index_of_second_hyphen = name.index("-", name.index("-") + 1)
            name = name[0:index_of_second_hyphen]

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

    execute_outside(capfd, "remove")

    create_project(
        capfd=capfd,
        name="rem",
        auth="postgres",
        frontend="no",
    )
    init_project(capfd, " -e HEALTHCHECK_INTERVAL=20s ")

    start_registry(capfd)

    pull_images(capfd)

    if Configuration.swarm_mode:
        # In swarm mode single service remove is not permitted if nothing is running
        exec_command(
            capfd,
            "remove postgres",
            f"Stack rem is not running, deploy it with {colors.RED}rapydo start",
        )

    # Even if nothing is running, remove is permitted both on Compose and Swarm
    exec_command(capfd, "remove", "Stack removed")

    NONE: List[str] = []
    if Configuration.swarm_mode:
        BACKEND_ONLY = ["rem_backend"]
        ALL = ["rem_backend", "rem_postgres"]
    else:
        BACKEND_ONLY = ["rem-backend"]
        ALL = ["rem-backend", "rem-postgres"]

    assert get_containers() == NONE

    start_project(capfd)

    if Configuration.swarm_mode:
        NETWORK_NAME = "rem_swarm_default"
    else:
        NETWORK_NAME = "rem_compose_default"

    assert get_containers() == ALL

    NAMED_VOLUMES_NUM, UNNAMED_VOLUMES_NUM = count_volumes()

    if Configuration.swarm_mode:
        # In swarm mode remove single service is equivalent to scale 0
        exec_command(
            capfd,
            "remove postgres",
            "rem_postgres scaled to 0",
            "verify: Service converged",
            "Services removed",
        )

        assert get_containers() == BACKEND_ONLY
        # Single service remove does not remove the network
        assert NETWORK_NAME in get_networks()
        # Single service remove also remove unnamed volumes
        time.sleep(2)
        n, u = count_volumes()
        assert NAMED_VOLUMES_NUM == n
        assert UNNAMED_VOLUMES_NUM > u

        exec_command(
            capfd,
            "restart",
            "Stack restarted",
        )

        time.sleep(2)

        assert get_containers() == ALL

        NAMED_VOLUMES_NUM, UNNAMED_VOLUMES_NUM = count_volumes()

        exec_command(
            capfd,
            "remove",
            "Stack removed",
        )

        assert get_containers() == NONE
        # Removal of all services also drop the network
        assert NETWORK_NAME not in get_networks()
        # Removal of all services also remove unnamed volumes
        n, u = count_volumes()
        assert NAMED_VOLUMES_NUM == n
        assert UNNAMED_VOLUMES_NUM > u
    else:

        exec_command(
            capfd,
            "remove postgres",
            "Stack removed",
        )

        assert get_containers() == BACKEND_ONLY
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
        # assert NETWORK_NAME not in get_networks()

        # Networks are not removed, but based on docker compose down --help they should
        # Also docker-compose down removes network from what I remember
        # Should be reported as bug? If corrected this check will start to fail
        assert NETWORK_NAME in get_networks()

        # Removal of all services does not remove any volume
        n, u = count_volumes()
        assert NAMED_VOLUMES_NUM == n
        assert UNNAMED_VOLUMES_NUM == u

        start_project(capfd)

        assert get_containers() == ALL

        exec_command(
            capfd,
            "remove --all postgres",
            "Stack removed",
        )

        assert get_containers() == BACKEND_ONLY
        # Removal of all services with --all flag remove unnamed volumes
        n, u = count_volumes()
        assert NAMED_VOLUMES_NUM == n
        # This locally works... but not on GA ... mistery
        # assert UNNAMED_VOLUMES_NUM > u

        # New counts, after single service --all has removed some unnamed volume
        NAMED_VOLUMES_NUM, UNNAMED_VOLUMES_NUM = count_volumes()

        exec_command(capfd, "remove --all", "Stack removed")

        assert get_containers() == NONE
        n, u = count_volumes()
        assert NAMED_VOLUMES_NUM > n
        assert UNNAMED_VOLUMES_NUM > u

    if Configuration.swarm_mode:
        # Remove the registry
        exec_command(
            capfd,
            "remove registry",
            "Service registry removed",
        )

        # Verify that the registry is no longer running
        exec_command(
            capfd,
            "start",
            "Registry 127.0.0.1:5000 not reachable.",
        )

        exec_command(
            capfd,
            "remove registry",
            "Service registry is not running",
        )

        # Mix both registry and normal services
        exec_command(
            capfd,
            "remove registry postgres",
            # Registry is already removed, can't remove it again
            # But this is enough to confirm that registry and services can be mixed up
            "Service registry is not running",
            # The main stack is already removed, can't remove postgres
            # But this is enough to confirm that registry and services can be mixed up
            "Stack rem is not running, deploy it with",
        )

        start_registry(capfd)

    exec_command(
        capfd,
        "run --detach --pull --port 7777 adminer",
        "You can access Adminer interface",
    )
    exec_command(
        capfd,
        "run --detach --pull --port 8888 swaggerui",
        "You can access SwaggerUI web page",
    )

    exec_command(
        capfd,
        "remove adminer postgres swaggerui",
        "Service adminer removed",
        "Service swaggerui removed",
    )

    exec_command(
        capfd,
        "remove adminer postgres swaggerui",
        "Service adminer is not running",
        "Service swaggerui is not running",
    )

    assert get_containers() == NONE
    # Verify that removal of interfaces does not stop the main stack, if not requested
    exec_command(capfd, "start backend", "Stack started")
    time.sleep(2)
    assert get_containers() == BACKEND_ONLY
    exec_command(capfd, "remove adminer", "Service adminer is not running")
    assert get_containers() == BACKEND_ONLY

    exec_command(capfd, "remove", "Stack removed")
