import time
from pathlib import Path

import typer
from python_on_whales import docker
from python_on_whales.utils import DockerException

from controller import __version__, log, print_and_exit
from controller.app import Application
from controller.packages import Packages


@Application.app.command(help="Execute controller tests")
def test(
    test: str = typer.Argument(None, help="Name of the test to be executed"),
    swarm_mode: bool = typer.Option(
        False,
        "--swarm",
        help="Execute the test in swarm mode",
        show_default=False,
    ),
    no_remove: bool = typer.Option(
        False,
        "--no-rm",
        help="Do not remove the container",
        show_default=False,
    ),
    # I have no need to test a command to locally execute tests
    # and I would like to preventany recursive test execution!
) -> None:  # pragma: no cover

    Application.print_command(
        Application.serialize_parameter("--swarm", swarm_mode, IF=swarm_mode),
        Application.serialize_parameter("--no-rm", no_remove, IF=no_remove),
        Application.serialize_parameter("", test),
    )

    controller_path = Packages.get_installation_path("rapydo")

    # Can't really happen...
    if not controller_path:  # pragma: no cover
        print_and_exit("Controller path not found")

    if not test:
        log.info("Choose a test to be executed:")
        for f in sorted(controller_path.joinpath("tests").glob("test_*.py")):
            test_name = f.with_suffix("").name.replace("test_", "")

            print(f"  - {test_name}")
        return None

    test_file = Path("tests", f"test_{test}.py")

    if not controller_path.joinpath(test_file).exists():
        print_and_exit("Invalid test name {}", test)

    image_name = f"rapydo/controller:{__version__}"
    container_name = "controller"

    docker.image.pull(image_name)

    if docker.container.exists(container_name):
        docker.container.remove(container_name, force=True, volumes=True)

    docker.container.run(
        image_name,
        detach=True,
        privileged=True,
        remove=True,
        volumes=[(controller_path, "/code")],
        name=container_name,
        envs={
            "TESTING": "1",
            "SWARM_MODE": "1" if swarm_mode else "0",
        },
    )

    docker.container.execute(
        container_name,
        command="syslogd",
        interactive=False,
        tty=False,
        stream=False,
        detach=True,
    )

    # Wait few seconds to let the docker daemon to start
    log.info("Waiting for docker daemon to start...")
    time.sleep(3)

    command = ["py.test", "-s", "-x", f"/code/{test_file}"]
    log.info("Executing command: {}", " ".join(command))

    try:
        docker.container.execute(
            container_name,
            command=command,
            workdir="/tmp",
            interactive=True,
            tty=True,
            stream=False,
            detach=False,
        )
    except DockerException as e:
        log.error(e)

    # Do not remove the container to let for some debugging
    if not no_remove:
        docker.container.remove(container_name, force=True, volumes=True)
        log.info("Test container ({}) removed", container_name)
