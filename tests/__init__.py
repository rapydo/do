import os
import sys
from collections import OrderedDict  # can be removed from python 3.7
from importlib import reload

from typer.testing import CliRunner

runner = CliRunner()


class TemporaryRemovePath:
    def __init__(self, path):
        self.path = os.path.abspath(path)
        self.tmp_path = f"{self.path}.bak"

    def __enter__(self):

        os.rename(self.path, self.tmp_path)
        return self

    def __exit__(self, _type, value, tb):
        os.rename(self.tmp_path, self.path)


class Timeout(Exception):
    pass


def signal_handler(signum, frame):
    raise Timeout("Time is up")


def mock_KeyboardInterrupt(signum, frame):
    raise KeyboardInterrupt("Time is up")


def exec_command(capfd, command, *asserts, input_text=None):

    import controller

    reload(controller)

    with capfd.disabled():
        print("\n", file=sys.stderr)
        print("_____________________________________________", file=sys.stderr)
        print(f"rapydo {command}", file=sys.stderr)

    from controller.app import Application
    from controller.project import Project

    ctrl = Application()

    # re-read everytime before invoking a command to cleanup the Configuration class
    Application.load_projectrc()
    Application.project_scaffold = Project()
    Application.gits = OrderedDict()
    result = runner.invoke(ctrl.app, command, input=input_text)

    with capfd.disabled():
        print(f"Exit code: {result.exit_code}", file=sys.stderr)
        print(result.stdout, file=sys.stderr)
        print("_____________________________________________", file=sys.stderr)

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
            print(f"{e}", file=sys.stderr)
        for o in cout:
            print(f">> {o}", file=sys.stderr)
        for o in out:
            print(f"_ {o}", file=sys.stderr)
        if result.exception and str(result.exception) != result.exit_code:
            print("\n!! Exception:", file=sys.stderr)
            print(result.exception, file=sys.stderr)

    for a in asserts:
        # Check if the assert is in any line (also as substring) from out or err
        assert a in out + err or any(a in x for x in out + err + cout + exc)

    return out


def create_project(
    capfd,
    name,
    auth="postgres",
    frontend="angular",
    services=None,
    extra="",
    init=False,
    pull=False,
    start=False,
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

    if init:
        exec_command(
            capfd,
            "init",
            "Project initialized",
        )

    if pull:
        exec_command(
            capfd,
            "pull",
            "Images pulled from docker hub",
        )

    if start:
        exec_command(
            capfd,
            "start",
            "docker-compose command: 'up'",
            "Stack started",
        )
