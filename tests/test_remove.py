"""
This module will test the remove command
"""
from typing import List

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

    # Return the containers sorted by name
    return sorted(containers)


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
    else:

        exec_command(
            capfd,
            "remove",
            "Stack removed",
        )

        assert get_containers() == NONE

        exec_command(
            capfd,
            "remove --all backend",
            "Stack removed",
        )

        assert get_containers() == NONE

        exec_command(
            capfd, "remove --all", "--all option not implemented yet", "Stack removed"
        )
