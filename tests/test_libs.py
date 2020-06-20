import tempfile

import pytest
from plumbum.commands.processes import ProcessExecutionError

from controller import __version__, gitter
from controller.utilities import system
from controller.utilities.configuration import load_yaml_file, mix_configuration

# These tests will directly access to functions, to verify cases
# not easly testable through cli commands:


def test_all(capfd):

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
    assert not gitter.switch_branch(do_repo, branch_name="0.7.3", remote=False)

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
        load_yaml_file("pyproject.toml", "tests")
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
