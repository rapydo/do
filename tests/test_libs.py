import os
import tempfile
from distutils.version import LooseVersion
from pathlib import Path

import pytest

from controller import __version__, gitter, log
from controller.app import Application
from controller.compose import Compose
from controller.packages import Packages
from controller.templating import Templating
from controller.utilities import services, system
from controller.utilities.configuration import load_yaml_file, mix_configuration

# These tests will directly access to functions, to verify cases
# not easly testable through cli commands:


def test_all(capfd):

    app = Application()

    values = app.autocomplete_service("")
    assert len(values) > 0
    assert "backend" in values
    values = app.autocomplete_service("invalid")
    assert len(values) == 0
    values = app.autocomplete_service("b")
    assert len(values) >= 1
    assert "backend" in values

    values = app.autocomplete_allservice("")
    assert len(values) > 0
    assert "backend" in values
    values = app.autocomplete_allservice("invalid")
    assert len(values) == 0
    values = app.autocomplete_allservice("b")
    assert len(values) >= 1
    assert "backend" in values
    values = app.autocomplete_allservice("c")
    assert len(values) >= 1
    assert "backend" not in values

    values = app.autocomplete_submodule("")
    assert len(values) > 0
    assert "main" in values
    values = app.autocomplete_submodule("invalid")
    assert len(values) == 0
    values = app.autocomplete_submodule("m")
    assert len(values) >= 1
    assert "main" in values
    values = app.autocomplete_submodule("d")
    assert len(values) >= 1
    assert "main" not in values

    values = app.autocomplete_interfaces("")
    assert len(values) > 0
    assert "swagger" in values
    assert "sqlalchemy" in values
    assert "mongo" in values
    assert "celery" in values
    values = app.autocomplete_interfaces("invalid")
    assert len(values) == 0
    values = app.autocomplete_interfaces("s")
    assert len(values) >= 1
    assert "swagger" in values
    assert "sqlalchemy" in values
    assert "celery" not in values
    values = app.autocomplete_interfaces("c")
    assert len(values) >= 1
    assert "swagger" not in values
    assert "sqlalchemy" not in values
    assert "celery" in values

    os.unlink(".rapydo")
    values = app.autocomplete_service("")
    assert len(values) == 0
    values = app.autocomplete_allservice("")
    assert len(values) == 0
    values = app.autocomplete_submodule("")
    assert len(values) == 0

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
        pytest.fail("ExecutionException not raised!")
    except system.ExecutionException:
        pass
    except BaseException:
        pytest.fail("Unexpected exception raised")

    # Invalid file / path
    try:
        load_yaml_file("invalid", "path")
        pytest.fail("No exception raised")
    except AttributeError:
        pass

    try:
        load_yaml_file(Path("invalid"), "path")
        pytest.fail("No exception raised")
    except AttributeError:
        pass

    try:
        load_yaml_file(Path("invalid"), Path("path"))
        pytest.fail("No exception raised")
    except SystemExit:
        pass

    y = load_yaml_file(Path("invalid"), Path("path"), is_optional=True)
    assert y is not None
    assert isinstance(y, dict)
    assert len(y) == 0

    try:
        load_yaml_file(Path("invalid"), Path("projects"))
        pytest.fail("No exception raised")
    except SystemExit:
        pass

    # Valid path, but not in yaml format
    try:
        load_yaml_file(Path("pyproject.toml"), Path(os.curdir))
        pytest.fail("No exception raised")
    except SystemExit:
        pass

    # File is empty
    f = tempfile.NamedTemporaryFile()
    try:
        load_yaml_file(Path(f.name), Path(os.curdir))
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

    shorten = services.get_celerybeat_scheduler
    env = {}
    assert shorten(env) == "Unknown"

    # Both ACTIVATE_CELERYBEAT and CELERY_BACKEND are required
    env["ACTIVATE_CELERYBEAT"] = "0"
    assert shorten(env) == "Unknown"
    env["ACTIVATE_CELERYBEAT"] = "1"
    assert shorten(env) == "Unknown"
    env["CELERY_BACKEND"] = "??"
    assert shorten(env) == "Unknown"
    # This is valid, but ACTIVATE_CELERYBEAT is still missing
    env["CELERY_BACKEND"] = "MONGODB"
    env["ACTIVATE_CELERYBEAT"] = "0"
    assert shorten(env) == "Unknown"
    env["ACTIVATE_CELERYBEAT"] = "1"
    assert shorten(env) == "celerybeatmongo.schedulers.MongoScheduler"
    env["CELERY_BACKEND"] = "REDIS"
    assert shorten(env) == "redbeat.RedBeatScheduler"
    env["CELERY_BACKEND"] = "INVALID"
    assert shorten(env) == "Unknown"

    assert services.get_default_user("invalid", "angular") is None
    assert services.get_default_user("backend", "") == "developer"
    assert services.get_default_user("celery", "") == "developer"
    assert services.get_default_user("celeryui", "") == "developer"
    assert services.get_default_user("celery-beat", "") == "developer"
    assert services.get_default_user("frontend", "invalid") is None
    assert services.get_default_user("frontend", "no") is None
    assert services.get_default_user("frontend", "angular") == "node"
    assert services.get_default_user("frontend", "angularjs") is None
    assert services.get_default_user("frontend", "react") is None
    assert services.get_default_user("postgres", "") == "postgres"
    assert services.get_default_user("neo4j", "") == "neo4j"

    assert services.get_default_command("invalid") == "bash"
    assert services.get_default_command("backend") == "restapi launch"
    assert services.get_default_command("neo4j") == "bin/cypher-shell"
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
    assert len(cmd) == 2
    assert cmd[0] is None
    assert isinstance(cmd[1], list)
    assert len(cmd[1]) == 0

    cmd = Compose.split_command("")
    assert len(cmd) == 2
    assert cmd[0] is None
    assert isinstance(cmd[1], list)
    assert len(cmd[1]) == 0

    cmd = Compose.split_command("a")
    assert len(cmd) == 2
    assert cmd[0] == "a"
    assert isinstance(cmd[1], list)
    assert len(cmd[1]) == 0

    cmd = Compose.split_command("a b")
    assert len(cmd) == 2
    assert cmd[0] == "a"
    assert isinstance(cmd[1], list)
    assert len(cmd[1]) == 1
    assert cmd[1][0] == "b"

    cmd = Compose.split_command("a b c")
    assert len(cmd) == 2
    assert cmd[0] == "a"
    assert isinstance(cmd[1], list)
    assert len(cmd[1]) == 2
    assert cmd[1][0] == "b"
    assert cmd[1][1] == "c"

    cmd = Compose.split_command("a 'b c'")
    assert len(cmd) == 2
    assert cmd[0] == "a"
    assert isinstance(cmd[1], list)
    assert len(cmd[1]) == 1
    assert cmd[1][0] == "b c"

    assert Packages.import_package("invalid") is None
    assert Packages.package_version("invalid") is None

    assert Packages.get_bin_version("invalid") is None

    v = Packages.get_bin_version("git")
    assert v is not None
    vv = LooseVersion(v)
    # Something like 2.25.1
    assert len(vv.version) == 3
    assert isinstance(vv.version[0], int)
    assert isinstance(vv.version[1], int)
    assert isinstance(vv.version[2], int)

    # Check docker client version
    v = Packages.get_bin_version("docker")
    assert v is not None
    vv = LooseVersion(v)
    # Something like 19.03.8 or 18.06.0-ce
    assert len(vv.version) >= 3
    assert isinstance(vv.version[0], int)
    assert isinstance(vv.version[1], int)
    assert isinstance(vv.version[2], int)

    # Check docker engine version
    v = Packages.get_bin_version(
        "docker", option=["version", "--format", "'{{.Server.Version}}'"]
    )
    assert v is not None
    vv = LooseVersion(v)
    assert len(vv.version) >= 3
    assert isinstance(vv.version[0], int)
    assert isinstance(vv.version[1], int)
    assert isinstance(vv.version[2], int)
