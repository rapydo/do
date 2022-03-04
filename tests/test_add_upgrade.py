"""
This module will test the add and upgrade commands
"""

import shutil
from pathlib import Path

from tests import Capture, create_project, exec_command, execute_outside, init_project

PROJECT_NAME = "second"
BACKEND_PATH = Path(f"projects/{PROJECT_NAME}/backend")
FRONTEND_PATH = Path(f"projects/{PROJECT_NAME}/frontend")
ENDPOINT_NAME = "xyz"
ENDPOINT_PATH = BACKEND_PATH.joinpath("endpoints", f"{ENDPOINT_NAME}.py")
PYTEST_PATH = BACKEND_PATH.joinpath("tests", f"test_endpoints_{ENDPOINT_NAME}.py")


def test_execute_outside(capfd: Capture) -> None:
    execute_outside(capfd, "add endpoint x")
    execute_outside(capfd, "upgrade --path x")


def test_add_create_and_init_project(capfd: Capture) -> None:
    create_project(
        capfd=capfd,
        name=PROJECT_NAME,
        auth="postgres",
        frontend="angular",
    )
    init_project(capfd)


def test_add_endpoint(capfd: Capture) -> None:
    assert not ENDPOINT_PATH.exists()
    assert not PYTEST_PATH.exists()
    exec_command(
        capfd,
        f"add endpoint {ENDPOINT_NAME} --add-tests",
        f"Endpoint created: {ENDPOINT_PATH}",
        f"Tests scaffold created: {PYTEST_PATH}",
    )


def test_add_endpoint_already_exists(capfd: Capture) -> None:
    exec_command(
        capfd,
        f"add endpoint {ENDPOINT_NAME}",
        f"{ENDPOINT_PATH} already exists",
    )


def test_add_endpoint_force(capfd: Capture) -> None:
    exec_command(
        capfd,
        f"add --force endpoint {ENDPOINT_NAME}",
        f"Endpoint created: {ENDPOINT_PATH}",
    )
    assert ENDPOINT_PATH.is_file()
    assert PYTEST_PATH.is_file()


def test_add_task(capfd: Capture) -> None:
    path = BACKEND_PATH.joinpath("tasks/xyz.py")
    assert not path.exists()
    exec_command(
        capfd,
        "add task xyz --add-tests",
        f"Task created: {path}",
        "Tests for tasks not implemented yet",
    )
    exec_command(
        capfd,
        "add task xyz",
        f"{path} already exists",
    )
    exec_command(
        capfd,
        "add --force task xyz",
        f"Task created: {path}",
    )
    assert path.is_file()


def test_add_component(capfd: Capture) -> None:
    path = FRONTEND_PATH.joinpath("app/components/xyz")
    test_path = FRONTEND_PATH.joinpath("app/components/xyz/xyz.spec.ts")
    assert not path.exists()
    assert not path.joinpath("xyz.ts").exists()
    assert not path.joinpath("xyz.html").exists()
    exec_command(
        capfd,
        "add component xyz --add-tests",
        "Added import { XyzComponent } from '@app/components/xyz/xyz'; to module ",
        "Added XyzComponent to module declarations",
        f"Component created: {path}",
        f"Tests scaffold created: {test_path}",
    )

    assert path.is_dir()
    assert path.joinpath("xyz.ts").is_file()
    assert path.joinpath("xyz.html").is_file()
    exec_command(
        capfd,
        "add component xyz",
        f"{path}/xyz.ts already exists",
    )
    exec_command(
        capfd,
        "add --force component xyz",
        f"Component created: {path}",
    )
    shutil.rmtree(path)
    exec_command(
        capfd,
        "add component xyz",
        "Import already included in module file",
        "Added XyzComponent to module declarations",
        f"Component created: {path}",
    )

    exec_command(
        capfd,
        "add component sink",
        "Added route to module declarations",
        "Added SinkComponent to module declarations",
    )


def test_add_service(capfd: Capture) -> None:
    path = FRONTEND_PATH.joinpath("app/services")
    assert not path.exists()
    assert not path.joinpath("xyz.ts").exists()
    exec_command(
        capfd,
        "add service xyz --add-tests",
        "Added import { XyzService } from '@app/services/xyz'; to module file",
        "Added XyzService to module declarations",
        f"Service created: {path}",
        "Tests for services not implemented yet",
    )
    assert path.is_dir()
    assert path.joinpath("xyz.ts").is_file()
    exec_command(
        capfd,
        "add service xyz",
        f"{path}/xyz.ts already exists",
    )
    exec_command(
        capfd,
        "add --force service xyz",
        f"Service created: {path}",
    )
    path.joinpath("xyz.ts").unlink()
    exec_command(
        capfd,
        "add service xyz",
        "Import already included in module file",
        "Added XyzService to module declarations",
        f"Service created: {path}",
    )


def test_add_integration_test(capfd: Capture) -> None:
    path = FRONTEND_PATH.joinpath("integration/app_mypath_my_id.spec.ts")
    assert not path.exists()
    exec_command(
        capfd,
        "add integration_test app/mypath/:my_id --add-tests",
        "Add integration_test does not support --add-tests flag",
    )

    exec_command(
        capfd,
        "add integration_test app/mypath/:my_id",
        f"Integration test created: {path}",
    )
    exec_command(
        capfd,
        "add integration_test app/mypath/:my_id",
        f"{path} already exists",
    )
    # Here a little variant, by adding a leading /
    exec_command(
        capfd,
        "add --force integration_test /app/mypath/:my_id",
        f"Integration test created: {path}",
    )
    assert path.is_file()


def test_add_workflow(capfd: Capture) -> None:
    path = Path(".github/workflows/github_actions-backend.yml")
    assert not path.exists()

    exec_command(
        capfd,
        "add workflow unexpectedname",
        "Invalid workflow name, expected: backend, frontend, cypress, mypy",
    )

    exec_command(
        capfd,
        "add workflow backend --add-tests",
        "Add workflow does not support --add-tests flag",
    )

    exec_command(
        capfd,
        "add workflow backend",
        f"GitHub Actions workflow created: {path}",
    )

    exec_command(
        capfd,
        "add workflow backend",
        f"{path} already exists",
    )
    exec_command(
        capfd,
        "add --force workflow backend",
        f"GitHub Actions workflow created: {path}",
    )
    assert path.is_file()

    exec_command(
        capfd,
        "add abc xyz",
        "Invalid value for",
        "'abc' is not one of 'endpoint', 'task', 'component', 'service', ",
    )


def test_upgrade_invalid_path(capfd: Capture) -> None:
    exec_command(
        capfd, "upgrade --path invalid", "Invalid path, cannot upgrade invalid"
    )


def test_upgrade(capfd: Capture) -> None:
    exec_command(capfd, "upgrade --path .gitignore")
