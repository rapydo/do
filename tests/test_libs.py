"""
This module will directly access to functions,
to verify cases not easly testable through cli commands
"""

import os
import re
import tempfile
from distutils.version import LooseVersion
from pathlib import Path
from typing import Dict, Union

import pytest
from faker import Faker

from controller import __version__
from controller.app import Application
from controller.commands.compose.backup import get_date_pattern
from controller.commands.install import download
from controller.deploy.compose import Compose
from controller.packages import Packages
from controller.templating import Templating
from controller.utilities import git, services, system
from controller.utilities.configuration import load_yaml_file, mix_configuration
from tests import Capture, create_project, init_project, random_project_name


def test_all(capfd: Capture, faker: Faker) -> None:

    create_project(
        capfd=capfd,
        name=random_project_name(faker),
    )
    init_project(capfd)

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

    os.unlink(".rapydo")
    values = app.autocomplete_service("")
    assert len(values) == 0
    values = app.autocomplete_allservice("")
    assert len(values) == 0
    values = app.autocomplete_submodule("")
    assert len(values) == 0

    assert git.get_repo("does/not/exist") is None
    do_repo = git.get_repo("submodules/do")
    assert do_repo is not None
    assert git.get_active_branch(None) is None
    assert git.get_active_branch(do_repo) == __version__
    assert not git.switch_branch(do_repo, branch_name=None)
    # Same branch => no change => return True
    assert git.switch_branch(do_repo, branch_name=__version__)
    assert not git.switch_branch(do_repo, branch_name="XYZ")

    assert git.switch_branch(do_repo, branch_name="0.7.3")
    assert git.get_active_branch(do_repo) == "0.7.3"
    assert git.switch_branch(do_repo, branch_name=__version__)
    assert git.get_active_branch(do_repo) == __version__

    assert git.get_origin(None) is None
    assert git.get_origin("not-a-git-object") is None
    assert git.get_active_branch("not-a-git-object") is None

    r = git.get_repo(".")
    assert git.get_origin(r) == "https://your_remote_git/your_project.git"

    # Create an invalid repo (i.e. without any remote)
    r = git.init("../justatest")
    assert git.get_origin(r) is None

    out = system.execute_command("echo", ["-n", "Hello World"])
    assert out == "Hello World"

    out = system.execute_command("echo", ["Hello World"])
    assert out == "Hello World\n"

    with pytest.raises(system.ExecutionException):
        assert system.execute_command("ls", ["doesnotexistforsure"])

    assert system.bytes_to_str(0) == "0"
    assert system.bytes_to_str(1) == "1"
    assert system.bytes_to_str(1023) == "1023"
    assert system.bytes_to_str(1024) == "1KB"
    assert system.bytes_to_str(1424) == "1KB"
    assert system.bytes_to_str(1824) == "2KB"
    assert system.bytes_to_str(18248) == "18KB"
    assert system.bytes_to_str(1024 * 1024 - 1) == "1024KB"
    assert system.bytes_to_str(1024 * 1024) == "1MB"
    assert system.bytes_to_str(18248377) == "17MB"
    assert system.bytes_to_str(418248377) == "399MB"
    assert system.bytes_to_str(1024 * 1024 * 1024 - 1) == "1024MB"
    assert system.bytes_to_str(1024 * 1024 * 1024) == "1GB"
    assert system.bytes_to_str(1024 * 1024 * 1024 * 1024 - 1) == "1024GB"
    assert system.bytes_to_str(1024 * 1024 * 1024 * 1024) == "1024GB"
    assert system.bytes_to_str(1024 * 1024 * 1024 * 1024 * 1024) == "1048576GB"

    assert system.str_to_bytes("0") == 0
    assert system.str_to_bytes("1") == 1
    assert system.str_to_bytes("42") == 42

    assert system.str_to_bytes("1K") == 1024
    assert system.str_to_bytes("1k") == 1024
    assert system.str_to_bytes("1KB") == 1024
    assert system.str_to_bytes("1kb") == 1024

    assert system.str_to_bytes("1M") == 1024 * 1024
    assert system.str_to_bytes("1m") == 1024 * 1024
    assert system.str_to_bytes("1MB") == 1024 * 1024
    assert system.str_to_bytes("1mb") == 1024 * 1024

    assert system.str_to_bytes("1G") == 1024 * 1024 * 1024
    assert system.str_to_bytes("1g") == 1024 * 1024 * 1024
    assert system.str_to_bytes("1GB") == 1024 * 1024 * 1024
    assert system.str_to_bytes("1gb") == 1024 * 1024 * 1024

    with pytest.raises(AttributeError):
        system.str_to_bytes("x")

    with pytest.raises(AttributeError):
        system.str_to_bytes("1T")

    with pytest.raises(AttributeError):
        system.str_to_bytes("1TB")

    # Invalid file / path
    with pytest.raises(SystemExit):
        load_yaml_file(file=Path("path", "invalid"))

    y = load_yaml_file(file=Path("path", "invalid"), is_optional=True)
    assert y is not None
    assert isinstance(y, dict)
    assert len(y) == 0

    with pytest.raises(SystemExit):
        load_yaml_file(file=Path("projects", "invalid"))

    # Valid path, but not in yaml format
    with pytest.raises(SystemExit):
        load_yaml_file(file=Path("pyproject.toml"))

    # File is empty
    f = tempfile.NamedTemporaryFile()
    with pytest.raises(SystemExit):
        load_yaml_file(file=Path(f.name))
    f.close()

    y = mix_configuration(None, None)
    assert y is not None
    assert isinstance(y, dict)
    assert len(y) == 0

    short1 = services.normalize_placeholder_variable
    assert short1("NEO4J_AUTH") == "NEO4J_PASSWORD"
    assert short1("POSTGRES_USER") == "ALCHEMY_USER"
    assert short1("POSTGRES_PASSWORD") == "ALCHEMY_PASSWORD"
    assert short1("MYSQL_USER") == "ALCHEMY_USER"
    assert short1("MYSQL_PASSWORD") == "ALCHEMY_PASSWORD"
    assert short1("RABBITMQ_DEFAULT_USER") == "RABBITMQ_USER"
    assert short1("RABBITMQ_DEFAULT_PASS") == "RABBITMQ_PASSWORD"
    assert short1("CYPRESS_AUTH_DEFAULT_USERNAME") == "AUTH_DEFAULT_USERNAME"
    assert short1("CYPRESS_AUTH_DEFAULT_PASSWORD") == "AUTH_DEFAULT_PASSWORD"
    assert short1("NEO4J_dbms_memory_heap_max__size") == "NEO4J_HEAP_SIZE"
    assert short1("NEO4J_dbms_memory_heap_initial__size") == "NEO4J_HEAP_SIZE"
    assert short1("NEO4J_dbms_memory_pagecache_size") == "NEO4J_PAGECACHE_SIZE"
    assert short1("MONGO_INITDB_ROOT_PASSWORD") == "MONGO_PASSWORD"
    assert short1("MONGO_INITDB_ROOT_USERNAME") == "MONGO_USER"

    key = "anyother"
    assert short1(key) == key

    short2 = services.get_celerybeat_scheduler
    env: Dict[str, Union[None, str, int, float]] = {}
    assert short2(env) == "Unknown"

    # Both ACTIVATE_CELERYBEAT and CELERY_BACKEND are required
    env["ACTIVATE_CELERYBEAT"] = "0"
    assert short2(env) == "Unknown"
    env["ACTIVATE_CELERYBEAT"] = "1"
    assert short2(env) == "Unknown"
    env["CELERY_BACKEND"] = "??"
    assert short2(env) == "Unknown"
    # This is valid, but ACTIVATE_CELERYBEAT is still missing
    env["CELERY_BACKEND"] = "MONGODB"
    env["ACTIVATE_CELERYBEAT"] = "0"
    assert short2(env) == "Unknown"
    env["ACTIVATE_CELERYBEAT"] = "1"
    assert short2(env) == "celerybeatmongo.schedulers.MongoScheduler"
    env["CELERY_BACKEND"] = "REDIS"
    assert short2(env) == "redbeat.RedBeatScheduler"
    env["CELERY_BACKEND"] = "INVALID"
    assert short2(env) == "Unknown"

    assert services.get_default_user("invalid", "angular") is None
    assert services.get_default_user("backend", "") == "developer"
    assert services.get_default_user("celery", "") == "developer"
    assert services.get_default_user("flower", "") == "developer"
    assert services.get_default_user("celery-beat", "") == "developer"
    assert services.get_default_user("frontend", "invalid") is None
    assert services.get_default_user("frontend", "no") is None
    assert services.get_default_user("frontend", "angular") == "node"
    assert services.get_default_user("frontend", "angularjs") is None
    assert services.get_default_user("postgres", "") == "postgres"
    assert services.get_default_user("neo4j", "") == "neo4j"

    assert services.get_default_command("invalid") == "bash"
    assert services.get_default_command("backend") == "restapi launch"
    assert services.get_default_command("bot") == "restapi bot"
    assert services.get_default_command("neo4j") == "bin/cypher-shell"
    assert "psql -U " in services.get_default_command("postgres")
    assert "mysql -D" in services.get_default_command("mariadb")

    templating = Templating()

    with pytest.raises(SystemExit):
        templating.get_template("invalid", {})

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

    with pytest.raises(SystemExit):
        Packages.check_program("invalid")

    v = Packages.check_program("docker")
    assert v is not None

    with pytest.raises(SystemExit):
        Packages.check_program("docker", min_version="99999.99")

    with pytest.raises(SystemExit):
        Packages.check_program("docker", max_version="0.0")

    v = Packages.check_program("docker", min_version="0.0")
    assert v is not None

    v = Packages.check_program("docker", max_version="99999.99")
    assert v is not None

    v = Packages.check_program("docker", min_version="0.0", max_version="99999.99")
    assert v is not None

    v = Packages.check_program(
        "docker",
        min_version="0.0",
        max_version="99999.99",
        min_recommended_version="99999.99",
    )
    assert v is not None

    assert Packages.get_installation_path("invalid") is None
    assert Packages.get_installation_path("rapydo") is not None
    assert Packages.get_installation_path("pip") is None

    date_pattern = get_date_pattern()
    # just a trick to transform a glob-like expression into a valid regular expression
    date_pattern.replace(".*", "\\.+")
    # Same pattern used in backup.py to create backup filenames
    d = faker.date("%Y_%m_%d-%H_%M_%S")
    for _ in range(20):
        assert re.match(date_pattern, f"{d}.bak")

    with pytest.raises(SystemExit):
        download("https://www.google.com/test")
