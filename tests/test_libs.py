"""
This module will directly access to functions,
to verify cases not easly testable through cli commands
"""

import os
import re
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Dict, Union

import pytest
from faker import Faker
from packaging.version import Version  # type: ignore

from controller import __version__
from controller.app import Application, Configuration
from controller.commands.backup import get_date_pattern
from controller.commands.install import download
from controller.commands.password import get_projectrc_variables_indentation
from controller.deploy.builds import get_image_creation
from controller.deploy.docker import Docker
from controller.packages import Packages
from controller.templating import Templating
from controller.utilities import git, services, system
from controller.utilities.configuration import load_yaml_file, mix_configuration
from tests import Capture, create_project, init_project, random_project_name


def test_autocomplete(capfd: Capture, faker: Faker) -> None:

    create_project(
        capfd=capfd,
        name=random_project_name(faker),
    )
    init_project(capfd)

    app = Application()

    values = app.autocomplete_service(None, None, "")  # type: ignore
    assert len(values) > 0
    assert "backend" in values
    values = app.autocomplete_service(None, None, "invalid")  # type: ignore
    assert len(values) == 0
    values = app.autocomplete_service(None, None, "b")  # type: ignore
    assert len(values) >= 1
    assert "backend" in values

    values = app.autocomplete_allservice(None, None, "")  # type: ignore
    assert len(values) > 0
    assert "backend" in values
    values = app.autocomplete_allservice(None, None, "invalid")  # type: ignore
    assert len(values) == 0
    values = app.autocomplete_allservice(None, None, "b")  # type: ignore
    assert len(values) >= 1
    assert "backend" in values
    values = app.autocomplete_allservice(None, None, "c")  # type: ignore
    assert len(values) >= 1
    assert "backend" not in values

    values = app.autocomplete_submodule(None, None, "")  # type: ignore
    assert len(values) > 0
    assert "main" in values
    values = app.autocomplete_submodule(None, None, "invalid")  # type: ignore
    assert len(values) == 0
    values = app.autocomplete_submodule(None, None, "m")  # type: ignore
    assert len(values) >= 1
    assert "main" in values
    values = app.autocomplete_submodule(None, None, "d")  # type: ignore
    assert len(values) >= 1
    assert "main" not in values

    os.unlink(".rapydo")
    values = app.autocomplete_service(None, None, "")  # type: ignore
    assert len(values) == 0
    values = app.autocomplete_allservice(None, None, "")  # type: ignore
    assert len(values) == 0
    values = app.autocomplete_submodule(None, None, "")  # type: ignore
    assert len(values) == 0


def test_git(capfd: Capture, faker: Faker) -> None:

    create_project(
        capfd=capfd,
        name=random_project_name(faker),
    )
    init_project(capfd)

    assert git.get_repo("does/not/exist") is None
    do_repo = git.get_repo("submodules/do")
    assert do_repo is not None
    assert git.get_active_branch(None) is None
    assert git.get_active_branch(do_repo) == __version__
    assert not git.switch_branch(None, branch_name="0.7.3")
    # Same branch => no change => return True
    assert git.switch_branch(do_repo, branch_name=__version__)
    assert not git.switch_branch(do_repo, branch_name="XYZ")

    assert git.switch_branch(do_repo, branch_name="0.7.3")
    assert git.get_active_branch(do_repo) == "0.7.3"
    assert git.switch_branch(do_repo, branch_name=__version__)
    assert git.get_active_branch(do_repo) == __version__

    assert git.get_origin(None) is None

    r = git.get_repo(".")
    assert git.get_origin(r) == "https://your_remote_git/your_project.git"

    # Create an invalid repo (i.e. without any remote)
    r = git.init("../justatest")
    assert git.get_origin(r) is None


def test_execute_command() -> None:
    out = system.execute_command("echo", ["-n", "Hello World"])
    assert out == "Hello World"

    out = system.execute_command("echo", ["Hello World"])
    assert out == "Hello World\n"

    with pytest.raises(system.ExecutionException):
        assert system.execute_command("ls", ["doesnotexistforsure"])


def test_bytes_to_str() -> None:
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


def test_str_to_bytes() -> None:
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


def test_load_yaml_file() -> None:
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


def test_mix_configuration() -> None:
    y = mix_configuration(None, None)
    assert y is not None
    assert isinstance(y, dict)
    assert len(y) == 0


def test_normalize_placeholder_variable() -> None:
    short1 = services.normalize_placeholder_variable
    assert short1("NEO4J_AUTH") == "NEO4J_PASSWORD"
    assert short1("POSTGRES_USER") == "ALCHEMY_USER"
    assert short1("POSTGRES_PASSWORD") == "ALCHEMY_PASSWORD"
    assert short1("MYSQL_USER") == "ALCHEMY_USER"
    assert short1("MYSQL_PASSWORD") == "ALCHEMY_PASSWORD"
    assert short1("DEFAULT_USER") == "RABBITMQ_USER"
    assert short1("DEFAULT_PASS") == "RABBITMQ_PASSWORD"
    assert short1("CYPRESS_AUTH_DEFAULT_USERNAME") == "AUTH_DEFAULT_USERNAME"
    assert short1("CYPRESS_AUTH_DEFAULT_PASSWORD") == "AUTH_DEFAULT_PASSWORD"
    assert short1("NEO4J_dbms_memory_heap_max__size") == "NEO4J_HEAP_SIZE"
    assert short1("NEO4J_dbms_memory_heap_initial__size") == "NEO4J_HEAP_SIZE"
    assert short1("NEO4J_dbms_memory_pagecache_size") == "NEO4J_PAGECACHE_SIZE"
    assert short1("MONGO_INITDB_ROOT_PASSWORD") == "MONGO_PASSWORD"
    assert short1("MONGO_INITDB_ROOT_USERNAME") == "MONGO_USER"

    key = "anyother"
    assert short1(key) == key


def test_get_celerybeat_scheduler() -> None:
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


def test_get_default_user() -> None:
    assert services.get_default_user("invalid") is None
    assert services.get_default_user("backend") == "developer"
    assert services.get_default_user("celery") == "developer"
    assert services.get_default_user("flower") == "developer"
    assert services.get_default_user("celerybeat") == "developer"
    Configuration.frontend = "invalid"
    assert services.get_default_user("frontend") is None
    Configuration.frontend = "no"
    assert services.get_default_user("frontend") is None
    Configuration.frontend = "angular"
    assert services.get_default_user("frontend") == "node"
    Configuration.frontend = "angularjs"
    assert services.get_default_user("frontend") is None
    assert services.get_default_user("postgres") == "postgres"
    assert services.get_default_user("neo4j") == "neo4j"
    assert services.get_default_user("redis") == "redis"


def test_get_default_command() -> None:
    assert services.get_default_command("invalid") == "bash"
    assert services.get_default_command("backend") == "restapi launch"
    assert services.get_default_command("bot") == "restapi bot"
    assert services.get_default_command("neo4j") == "bin/cypher-shell"
    assert services.get_default_command("registry") == "ash"
    assert "psql -U " in services.get_default_command("postgres")
    assert "mysql -D" in services.get_default_command("mariadb")


def test_get_templating() -> None:
    templating = Templating()

    with pytest.raises(SystemExit):
        templating.get_template("invalid", {})


def test_split_command() -> None:
    cmd = Docker.split_command(None)
    assert isinstance(cmd, list)
    assert len(cmd) == 0

    cmd = Docker.split_command("")
    assert isinstance(cmd, list)
    assert len(cmd) == 0

    cmd = Docker.split_command("a")
    assert isinstance(cmd, list)
    assert len(cmd) == 1
    assert cmd[0] == "a"

    cmd = Docker.split_command("a b")
    assert isinstance(cmd, list)
    assert len(cmd) == 2
    assert cmd[0] == "a"
    assert cmd[1] == "b"

    cmd = Docker.split_command("a b c")
    assert isinstance(cmd, list)
    assert len(cmd) == 3
    assert cmd[0] == "a"
    assert cmd[1] == "b"
    assert cmd[2] == "c"

    cmd = Docker.split_command("a 'b c'")
    assert isinstance(cmd, list)
    assert len(cmd) == 2
    assert cmd[0] == "a"
    assert cmd[1] == "b c"


def test_packages(faker: Faker) -> None:
    assert Packages.get_bin_version("invalid") is None

    v = Packages.get_bin_version("git")
    assert v is not None
    # Something like 2.25.1
    assert len(str(Version(v)).split(".")) == 3

    # Check docker client version
    v = Packages.get_bin_version("docker")
    assert v is not None
    # Something like 19.03.8 or 18.06.0-ce
    assert len(str(Version(v)).split(".")) >= 3

    # Check docker engine version
    v = Packages.get_bin_version(
        "docker", option=["version", "--format", "'{{.Server.Version}}'"]
    )
    assert v is not None
    assert len(str(Version(v)).split(".")) >= 3

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

    assert Packages.convert_bin_to_win32("test") == "test"
    assert Packages.convert_bin_to_win32("compose") == "compose"
    assert Packages.convert_bin_to_win32("buildx") == "buildx"
    assert Packages.convert_bin_to_win32("git") == "git"
    rand_str = faker.pystr()
    assert Packages.convert_bin_to_win32(rand_str) == rand_str
    assert Packages.convert_bin_to_win32("docker") == "docker.exe"


def test_download() -> None:
    with pytest.raises(SystemExit):
        download("https://www.google.com/test", "")

    with pytest.raises(SystemExit):
        download(
            "https://github.com/rapydo/do/archive/refs/tags/v1.2.zip",
            "thisisawrongchecksum",
        )

    downloaded = download(
        "https://github.com/rapydo/do/archive/refs/tags/v1.2.zip",
        "dc07bef0d12a7a9cfd0f383452cbcb6d",
    )
    assert downloaded is not None


def test_get_date_pattern(faker: Faker) -> None:
    date_pattern = get_date_pattern()
    # just a trick to transform a glob-like expression into a valid regular expression
    date_pattern.replace(".*", "\\.+")
    # Same pattern used in backup.py to create backup filenames
    d = faker.date("%Y_%m_%d-%H_%M_%S")
    for _ in range(20):
        assert re.match(date_pattern, f"{d}.bak")


def test_get_image_creation() -> None:
    _1970 = datetime.fromtimestamp(0)
    assert get_image_creation("invalid") == _1970


def test_get_projectrc_variables_indentation() -> None:
    assert get_projectrc_variables_indentation([]) == 0

    projectrc = """
project: xyz
""".split(
        "\n"
    )

    assert get_projectrc_variables_indentation(projectrc) == 0

    projectrc = """
project: xyz
project_configuration:
""".split(
        "\n"
    )

    assert get_projectrc_variables_indentation(projectrc) == 0

    projectrc = """
project: xyz
project_configuration:
  variables:
""".split(
        "\n"
    )

    assert get_projectrc_variables_indentation(projectrc) == 0

    projectrc = """
project: xyz
project_configuration:
  variables:
    env:
      X: 10
""".split(
        "\n"
    )

    assert get_projectrc_variables_indentation(projectrc) == 6

    projectrc = """
project: xyz
project_configuration:
 variables:
    env:
      X: 10
""".split(
        "\n"
    )

    assert get_projectrc_variables_indentation(projectrc) == 6

    projectrc = """
project: xyz
project_configuration:
 variables:
  env:
   X: 10
""".split(
        "\n"
    )

    assert get_projectrc_variables_indentation(projectrc) == 3

    projectrc = """
project: xyz
project_configuration:
 variables:
  env:
    X: 10
""".split(
        "\n"
    )

    assert get_projectrc_variables_indentation(projectrc) == 4

    projectrc = """
project: xyz
project_configuration:
 variables:
  env:
""".split(
        "\n"
    )

    assert get_projectrc_variables_indentation(projectrc) == 3

    projectrc = """
project: xyz
project_configuration:
 variables:
   env:
""".split(
        "\n"
    )

    assert get_projectrc_variables_indentation(projectrc) == 4

    projectrc = """
project: xyz
project_configuration:
  variables:
    env:
""".split(
        "\n"
    )

    assert get_projectrc_variables_indentation(projectrc) == 6

    projectrc = """
project: xyz
project_configuration:
    variables:
        env:
            X: 10
""".split(
        "\n"
    )

    assert get_projectrc_variables_indentation(projectrc) == 12
