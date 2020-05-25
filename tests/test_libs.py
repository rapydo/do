# -*- coding: utf-8 -*-
import pytest
from plumbum.commands.processes import ProcessExecutionError
from git.exc import InvalidGitRepositoryError

from controller import gitter
from controller import __version__
from controller.utilities import system

# These tests will directly access to functions, to verify cases
# not easly testable through cli commands:


def test_all(capfd):

    assert gitter.get_repo("does/not/exist") is None
    do_repo = gitter.get_repo("submodules/do")
    assert do_repo is not None
    assert gitter.get_active_branch(None) is None
    assert gitter.get_active_branch(do_repo) == __version__
    assert not gitter.switch_branch(do_repo, branch_name=None)
    assert not gitter.switch_branch(do_repo, branch_name=__version__)
    assert not gitter.switch_branch(do_repo, branch_name="XYZ")
    # non remote branch is not found, because we only fetched current version
    assert not gitter.switch_branch(do_repo, branch_name="0.7.3", remote=False)

    assert gitter.switch_branch(do_repo, branch_name="0.7.3")
    assert gitter.get_active_branch(do_repo) == "0.7.3"
    assert gitter.switch_branch(do_repo, branch_name=__version__)
    assert gitter.get_active_branch(do_repo) == __version__

    assert gitter.get_origin(None) is None
    assert gitter.get_origin('not-a-git-object') is None
    assert gitter.get_active_branch('not-a-git-object') is None

    r = gitter.get_repo(".")
    assert gitter.get_origin(r) == 'https://your_remote_git/your_project.git'

    # Create an invalid repo (i.e. without any remote)
    r = gitter.init("../justatest")
    assert gitter.get_origin(r) is None
    assert gitter.get_local(r) is None

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
