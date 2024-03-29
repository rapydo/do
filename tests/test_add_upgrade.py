"""
This module will test the add and upgrade commands
"""

import shutil
from pathlib import Path

from tests import Capture, create_project, exec_command, execute_outside, init_project


def test_add(capfd: Capture) -> None:
    execute_outside(capfd, "add endpoint x")
    execute_outside(capfd, "upgrade --path x")
    create_project(
        capfd=capfd,
        name="second",
        auth="postgres",
        frontend="angular",
    )
    init_project(capfd)

    path = Path("projects/second/backend/endpoints/xyz.py")
    test_path = Path("projects/second/backend/tests/test_endpoints_xyz.py")
    assert not path.exists()
    assert not test_path.exists()
    exec_command(
        capfd,
        "add endpoint xyz --add-tests",
        f"Endpoint created: {path}",
        f"Tests scaffold created: {test_path}",
    )
    exec_command(
        capfd,
        "add endpoint xyz",
        f"{path} already exists",
    )
    exec_command(
        capfd,
        "add --force endpoint xyz",
        f"Endpoint created: {path}",
    )
    assert path.is_file()
    assert test_path.is_file()

    path = Path("projects/second/backend/tasks/xyz.py")
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

    path = Path("projects/second/frontend/app/components/xyz")
    test_path = Path("projects/second/frontend/app/components/xyz/xyz.spec.ts")
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

    path = Path("projects/second/frontend/app/services")
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

    path = Path("projects/second/frontend/e2e/app_mypath_my_id.spec.ts")
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
        "'abc' is not one of 'endpoint', 'task', 'component',",
        "'service', 'integration_test', 'workflow'.",
    )

    exec_command(capfd, "upgrade")
    exec_command(
        capfd, "upgrade --path invalid", "Invalid path, cannot upgrade invalid"
    )
    exec_command(capfd, "upgrade --path .gitignore")
