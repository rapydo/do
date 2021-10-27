import os
import tempfile
import time
from datetime import datetime
from importlib import reload
from pathlib import Path
from types import TracebackType
from typing import Any, List, Optional, Type, TypeVar

from faker import Faker
from glom import glom
from python_on_whales import docker
from typer.testing import CliRunner

from controller import PROJECTRC, REGISTRY, SWARM_MODE
from controller.deploy.swarm import Swarm
from controller.utilities import configuration

runner = CliRunner()


# This does not work...
# from pytest.capture import CaptureFixture
# Capture = CaptureFixture[str]
Capture = Any

T = TypeVar("T", bound="TemporaryRemovePath")


class TemporaryRemovePath:
    def __init__(self, path: Path):
        self.path = path.absolute()
        self.tmp_path = self.path.with_suffix(f"{path.suffix}.bak")

    def __enter__(self: T) -> T:

        self.path.rename(self.tmp_path)
        return self

    def __exit__(
        self,
        _type: Optional[Type[Exception]],
        value: Optional[Exception],
        tb: Optional[TracebackType],
    ) -> bool:
        self.tmp_path.rename(self.path)
        # return False if the exception is not handled:
        # -> return True if the exception is None (nothing to be handled)
        # -> return False if the exception is not None (because it is not handled here)
        # always return False is not accepted by mypy...
        return _type is None


class Timeout(Exception):
    pass


def signal_handler(signum, frame):  # type: ignore
    raise Timeout("Time is up")


def mock_KeyboardInterrupt(signum, frame):  # type: ignore
    raise KeyboardInterrupt("Time is up")


def exec_command(capfd: Capture, command: str, *asserts: str) -> None:

    # This is needed to reload the LOG dir
    import controller

    reload(controller)

    with capfd.disabled():
        print("\n")
        print("_____________________________________________")
        print(f"rapydo {command}")

    from controller.app import Application
    from controller.project import Project

    ctrl = Application()

    # re-read everytime before invoking a command to cleanup the Configuration class
    Application.load_projectrc()
    Application.project_scaffold = Project()
    Application.gits = {}
    result = runner.invoke(ctrl.app, command)

    with capfd.disabled():
        print(f"Exit code: {result.exit_code}")
        print(result.stdout)
        print("_____________________________________________")

    captured = capfd.readouterr()

    # Here outputs from inside the containers
    cout = [x for x in captured.out.replace("\r", "").split("\n") if x.strip()]
    # Here output from rapydo
    err = [x for x in captured.err.replace("\r", "").split("\n") if x.strip()]
    # Here output from other sources, e.g. typer errors o docker-compose output
    out = [x for x in result.stdout.replace("\r", "").split("\n") if x.strip()]
    # Here exceptions, e.g. Time is up
    if result.exception:
        exc = [
            x for x in str(result.exception).replace("\r", "").split("\n") if x.strip()
        ]
    else:
        exc = []

    with capfd.disabled():
        for e in err:
            print(f"{e}")
        for o in cout:
            print(f">> {o}")
        for o in out:
            print(f"_ {o}")
        if result.exception and str(result.exception) != result.exit_code:
            print("\n!! Exception:")
            print(result.exception)

    for a in asserts:
        # Check if the assert is in any line (also as substring) from out or err
        assert a in out + err or any(a in x for x in out + err + cout + exc)


def service_verify(capfd: Capture, service: str) -> None:
    exec_command(
        capfd,
        f"shell backend 'restapi verify --service {service}'",
        f"Service {service} is reachable",
        f"{service} successfully authenticated on ",
    )


def random_project_name(faker: Faker) -> str:

    return f"{faker.word()}{faker.word()}".lower()


def create_project(
    capfd: Capture,
    name: Optional[str] = None,
    auth: str = "postgres",
    frontend: str = "angular",
    services: Optional[List[str]] = None,
    extra: str = "",
) -> None:

    opt = "--current --origin-url https://your_remote_git/your_project.git"
    s = ""
    if services:
        for service in services:
            s += f" --service {service}"

    exec_command(
        capfd,
        f"create {name} --auth {auth} --frontend {frontend} {opt} {extra} {s}",
        f"Project {name} successfully created",
    )


def init_project(capfd: Capture, pre_options: str = "", post_options: str = "") -> None:

    if "HEALTHCHECK_INTERVAL" not in pre_options:
        pre_options += " -e HEALTHCHECK_INTERVAL=1s "

    exec_command(
        capfd,
        f"{pre_options} init {post_options}",
        "Project initialized",
    )


def start_registry(capfd: Capture) -> None:
    if SWARM_MODE:
        exec_command(capfd, "run registry --pull")
        time.sleep(2)

        print(docker.logs(REGISTRY))


def pull_images(capfd: Capture) -> None:

    exec_command(
        capfd,
        "pull --quiet",
        "Base images pulled from docker hub",
    )


def start_project(capfd: Capture) -> None:
    exec_command(
        capfd,
        "start",
        "Stack started",
    )
    if SWARM_MODE:
        time.sleep(10)
    else:
        time.sleep(5)


def execute_outside(capfd: Capture, command: str) -> None:
    folder = os.getcwd()
    os.chdir(tempfile.gettempdir())
    exec_command(
        capfd,
        command,
        "You are not in a git repository",
    )

    os.chdir(folder)


def get_container_start_date(
    capfd: Capture, service: str, project_name: str, wait: bool = False
) -> datetime:

    # Optional is needed because swarm.get_container returns Optional[str]
    container_name: Optional[str] = None

    if service == REGISTRY:
        container_name = REGISTRY
    elif SWARM_MODE:
        if wait:
            # This is needed to debug and wait the service rollup to complete
            # Status is both for debug and to delay the get_container
            exec_command(capfd, "status")
            time.sleep(4)

        swarm = Swarm()
        container_name = swarm.get_container(service, slot=1)
    else:
        container_name = f"{project_name}_{service}_1"

    assert container_name is not None
    return docker.container.inspect(container_name).state.started_at


def get_variable_from_projectrc(variable: str) -> str:
    projectrc = configuration.load_yaml_file(file=PROJECTRC, is_optional=False)

    return glom(
        projectrc, f"project_configuration.variables.env.{variable}", default=""
    )
