# -*- coding: utf-8 -*-
from controller import gitter
from controller import __version__

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
    assert not gitter.switch_branch(do_repo, branch_name="0.7.2", remote=False)

    assert gitter.switch_branch(do_repo, branch_name="0.7.2")
    assert gitter.get_active_branch(do_repo) == "0.7.2"
    assert gitter.switch_branch(do_repo, branch_name=__version__)
    assert gitter.get_active_branch(do_repo) == __version__
