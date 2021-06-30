import time
from importlib import reload
from pathlib import Path
from types import TracebackType
from typing import Any, Optional, Type, TypeVar

from faker import Faker
from typer.testing import CliRunner

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
        _type: Optional[Type[BaseException]],
        value: Optional[BaseException],
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


def signal_handler(signum, frame):
    raise Timeout("Time is up")


def mock_KeyboardInterrupt(signum, frame):
    raise KeyboardInterrupt("Time is up")


def exec_command(capfd: Any, command: str, *asserts: str) -> None:

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


def service_verify(capfd: Any, service: str) -> None:
    exec_command(
        capfd,
        f"shell backend --no-tty 'restapi verify --service {service}'",
        f"Service {service} is reachable",
    )


def random_project_name(faker: Faker) -> str:

    return f"{faker.word()}{faker.word()}"


def create_project(
    capfd,
    name=None,
    auth="postgres",
    frontend="angular",
    services=None,
    extra="",
):

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


def init_project(capfd):
    exec_command(
        capfd,
        "init",
        "Project initialized",
    )


def pull_images(capfd):
    exec_command(
        capfd,
        "pull --quiet",
        "Base images pulled from docker hub",
    )


def start_project(capfd):
    exec_command(
        capfd,
        "start",
        "docker-compose command: 'up'",
        "Stack started",
    )
    time.sleep(5)
