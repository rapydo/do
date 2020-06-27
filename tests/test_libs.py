import os
import tempfile

import pytest
from plumbum.commands.processes import ProcessExecutionError

from controller import __version__, gitter, log
from controller.compose import Compose
from controller.templating import Templating
from controller.utilities import services, system
from controller.utilities.configuration import load_yaml_file, mix_configuration

# These tests will directly access to functions, to verify cases
# not easly testable through cli commands:


def test_all(capfd):

    if os.getenv("STAGE") == "no-docker":
        log.warning("Skipping test libs/all: docker is not enabled")
        return True

    assert gitter.get_repo("does/not/exist") is None
    do_repo = gitter.get_repo("submodules/do")
    assert do_repo is not None
    assert gitter.get_active_branch(None) is None
    assert gitter.get_active_branch(do_repo) == __version__
    assert not gitter.switch_branch(do_repo, branch_name=None)
    # Same branch => no change => return True
    assert gitter.switch_branch(do_repo, branch_name=__version__)
    assert not gitter.switch_branch(do_repo, branch_name="XYZ")
    # non remote branch is not found, because we only fetched current version
    # 0.7.3 is already test for automatic switch in editable mode,
    # i.e. local branch already exists and remote=False fails... let's use 0.7.2
    assert not gitter.switch_branch(do_repo, branch_name="0.7.2", remote=False)

    assert gitter.switch_branch(do_repo, branch_name="0.7.3")
    assert gitter.get_active_branch(do_repo) == "0.7.3"
    assert gitter.switch_branch(do_repo, branch_name=__version__)
    assert gitter.get_active_branch(do_repo) == __version__

    assert gitter.get_origin(None) is None
    assert gitter.get_origin("not-a-git-object") is None
    assert gitter.get_active_branch("not-a-git-object") is None

    r = gitter.get_repo(".")
    assert gitter.get_origin(r) == "https://your_remote_git/your_project.git"

    # Create an invalid repo (i.e. without any remote)
    r = gitter.init("../justatest")
    assert gitter.get_origin(r) is None

    out = system.execute_command("echo", ["-n", "Hello World"])
    assert out == "Hello World"

    out = system.execute_command("echo", "Hello World")
    assert out == "Hello World\n"

    try:
        assert system.execute_command("ls", "doesnotexistforsure")
        pytest.fail("ProcessExecutionError not raised!")
    except ProcessExecutionError:
        pass
    except BaseException:
        pytest.fail("Unexpected exception raised")

    # Invalid file / path
    try:
        load_yaml_file("invalid", "path")
        pytest.fail("No exception raised")
    except SystemExit:
        pass

    y = load_yaml_file("invalid", "path", is_optional=True)
    assert y is not None
    assert isinstance(y, dict)
    assert len(y) == 0

    try:
        load_yaml_file("invalid", "projects")
        pytest.fail("No exception raised")
    except SystemExit:
        pass

    # Valid path, but not in yaml format
    try:
        load_yaml_file("pyproject.toml", ".")
        pytest.fail("No exception raised")
    except SystemExit:
        pass

    # File is empty
    f = tempfile.NamedTemporaryFile()
    try:
        load_yaml_file(f.name, ".")
        pytest.fail("No exception raised")
    except SystemExit:
        pass
    f.close()

    y = mix_configuration(None, None)
    assert y is not None
    assert isinstance(y, dict)
    assert len(y) == 0

    shorten = services.normalize_placeholder_variable
    assert shorten("NEO4J_AUTH") == "NEO4J_PASSWORD"
    assert shorten("POSTGRES_USER") == "ALCHEMY_USER"
    assert shorten("POSTGRES_PASSWORD") == "ALCHEMY_PASSWORD"
    assert shorten("MYSQL_USER") == "ALCHEMY_USER"
    assert shorten("MYSQL_PASSWORD") == "ALCHEMY_PASSWORD"
    assert shorten("RABBITMQ_DEFAULT_USER") == "RABBITMQ_USER"
    assert shorten("RABBITMQ_DEFAULT_PASS") == "RABBITMQ_PASSWORD"
    key = "anyother"
    assert shorten(key) == key

    # os.rename(
    #     "submodules/do/controller/templates", "submodules/do/controller/templates.bak"
    # )
    # try:
    #     Templating()
    #     pytest.fail("No exception raised")
    # except SystemExit:
    #     pass

    # os.rename(
    #     "submodules/do/controller/templates.bak", "submodules/do/controller/templates"
    # )

    templating = Templating()

    try:
        templating.get_template("invalid", {})
        pytest.fail("No exception raised")
    except SystemExit:
        pass

    cmd = Compose.split_command(None)
    assert cmd[0] is None
    assert len(cmd) == 0

    cmd = Compose.split_command("a")
    assert cmd[0] is None
    assert len(cmd) == 0

    cmd = Compose.split_command("a b")
    assert cmd[0] == "a"
    assert len(cmd) == 1
    assert cmd[1] == "b"

    cmd = Compose.split_command("a b c")
    assert cmd[0] == "a"
    assert len(cmd) == 2
    assert cmd[1] == "b"
    assert cmd[2] == "c"
