"""
This module will test the add and upgrade commands
"""

import os
import shutil

from tests import create_project, exec_command


def test_add(capfd):

    create_project(
        capfd=capfd,
        name="second",
        auth="postgres",
        frontend="angular",
        init=True,
        pull=False,
        start=False,
    )

    path = "projects/second/backend/endpoints/xyz.py"
    test_path = "projects/second/backend/tests/test_endpoints_xyz.py"
    assert not os.path.exists(path)
    assert not os.path.exists(test_path)
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
    assert os.path.isfile(path)
    assert os.path.isfile(test_path)

    path = "projects/second/backend/tasks/xyz.py"
    assert not os.path.exists(path)
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
    assert os.path.isfile(path)

    path = "projects/second/frontend/app/components/xyz"
    test_path = "projects/second/frontend/app/components/xyz/xyz.spec.ts"
    assert not os.path.exists(path)
    assert not os.path.exists(os.path.join(path, "xyz.ts"))
    assert not os.path.exists(os.path.join(path, "xyz.html"))
    exec_command(
        capfd,
        "add component xyz --add-tests",
        "Added import { XyzComponent } from '@app/components/xyz/xyz'; to module ",
        "Added XyzComponent to module declarations",
        f"Component created: {path}",
        f"Tests scaffold created: {test_path}",
    )

    assert os.path.isdir(path)
    assert os.path.isfile(os.path.join(path, "xyz.ts"))
    assert os.path.isfile(os.path.join(path, "xyz.html"))
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

    path = "projects/second/frontend/app/services"
    assert not os.path.exists(path)
    assert not os.path.exists(os.path.join(path, "xyz.ts"))
    exec_command(
        capfd,
        "add service xyz --add-tests",
        "Added import { XyzService } from '@app/services/xyz'; to module file",
        "Added XyzService to module declarations",
        f"Service created: {path}",
        "Tests for services not implemented yet",
    )
    assert os.path.isdir(path)
    assert os.path.isfile(os.path.join(path, "xyz.ts"))
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
    os.remove(f"{path}/xyz.ts")
    exec_command(
        capfd,
        "add service xyz",
        "Import already included in module file",
        "Added XyzService to module declarations",
        f"Service created: {path}",
    )

    path = "projects/second/frontend/integration/app_mypath_my_id.spec.ts"
    assert not os.path.exists(path)
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
    assert os.path.isfile(path)

    exec_command(
        capfd,
        "add abc xyz",
        "invalid choice: abc. "  # Note no command
        "(choose from endpoint, task, component, service, integration_test)",
    )

    exec_command(capfd, "upgrade")
    exec_command(
        capfd, "upgrade --path invalid", "Invalid path, cannot upgrade invalid"
    )
    exec_command(capfd, "upgrade --path .gitignore")
