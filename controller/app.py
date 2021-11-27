import enum
import json
import os
import shutil
import sys
import time
import warnings
from distutils.version import LooseVersion
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple, Union, cast

import click
import requests
import typer
from git import Repo as GitRepo
from glom import glom
from python_on_whales import docker
from python_on_whales.utils import DockerException
from tabulate import tabulate
from zxcvbn import zxcvbn

from controller import (
    COMPOSE_ENVIRONMENT_FILE,
    CONFS_DIR,
    CONTAINERS_YAML_DIRNAME,
    DATAFILE,
    EXTENDED_PROJECT_DISABLED,
    PLACEHOLDER,
    PROJECT_DIR,
    PROJECTRC,
    RED,
    REGISTRY,
    SUBMODULES_DIR,
    SWARM_MODE,
    TABLE_FORMAT,
    YELLOW,
    ComposeServices,
    EnvType,
    __version__,
    log,
    print_and_exit,
)
from controller.commands import load_commands
from controller.packages import Packages
from controller.project import ANGULAR, NO_FRONTEND, Project
from controller.templating import Templating
from controller.utilities import configuration, git, services, system

warnings.simplefilter("always", DeprecationWarning)

ROOT_UID = 0
BASE_UID = 1000


CommandParameter = Union[int, str, bool, None, Path, Iterable[str], enum.Enum]


class Configuration:
    projectrc: Dict[str, str] = {}
    # To be better characterized. This is a:
    # {'variables': 'env': Dict[str, str]}
    host_configuration: Dict[str, Dict[str, Dict[str, str]]] = {}
    specs: Dict[str, str] = {}
    services_list: Optional[str]
    environment: Dict[str, str]

    action: Optional[str] = None
    parameters: List[str] = []

    production: bool = False
    testing: bool = False
    project: str = ""
    frontend: Optional[str] = None
    hostname: str = ""
    remote_engine: Optional[str] = None
    stack: str = ""
    load_backend: bool = False
    load_frontend: bool = False
    load_commons: bool = False

    version: str = ""
    rapydo_version: str = ""
    project_title: Optional[str] = None
    project_description: Optional[str] = None
    project_keywords: Optional[str] = None

    initialize: bool = False
    update: bool = False
    check: bool = False
    install: bool = False
    print_version: bool = False
    create: bool = False

    # It will be replaced with PROJECT_DIR/project
    ABS_PROJECT_PATH: Path = PROJECT_DIR

    # used by single-container commands (i.e. run) in swarm mode
    FORCE_COMPOSE_ENGINE: bool = False

    @staticmethod
    def set_action(action: Optional[str], params: Dict[str, Any]) -> None:
        Configuration.action = action
        Configuration.initialize = Configuration.action == "init"
        Configuration.update = Configuration.action == "update"
        Configuration.check = Configuration.action == "check"
        Configuration.install = Configuration.action == "install"
        Configuration.print_version = Configuration.action == "version"
        Configuration.create = Configuration.action == "create"

        params.pop("version")
        # This will start to fail when this parameter will be dropped
        params.pop("services_list")

        Configuration.parameters = []
        project = params.pop("project")
        if project and project != Configuration.projectrc.get("project"):
            Configuration.parameters.append(f"--project {project}")

        hostname = params.pop("hostname")
        if hostname != "localhost" and hostname != Configuration.projectrc.get(
            "hostname"
        ):
            Configuration.parameters.append(f"--hostname {hostname}")

        stack = params.pop("stack")
        if stack and stack != Configuration.projectrc.get("stack"):
            Configuration.parameters.append(f"--stack {stack}")

        if params.pop("production"):
            Configuration.parameters.append("--production")

        if params.pop("testing"):
            Configuration.parameters.append("--testing")

        environment = params.pop("environment")
        if environment:
            for e in environment:
                Configuration.parameters.append(f"--env {e}")

        remote_engine = params.pop("remote_engine")
        if remote_engine and stack:
            Configuration.parameters.append(f"--remote {remote_engine}")

        if params.pop("no_backend"):
            Configuration.parameters.append("--no-backend")
        if params.pop("no_frontend"):
            Configuration.parameters.append("--no-frontend")
        if params.pop("no_commons"):
            Configuration.parameters.append("--no-commons")

        if params:
            log.warning("Found unknown parameters: {}", params)


def projectrc_values(
    ctx: typer.Context, param: typer.CallbackParam, value: str
) -> Optional[str]:
    if ctx.resilient_parsing:  # pragma: no cover
        return None

    if not param.name or value != param.get_default(ctx):
        return value

    from_projectrc = Configuration.projectrc.get(param.name)

    if from_projectrc is not None:
        return from_projectrc

    return value


def version_callback(value: bool) -> None:
    if value:
        typer.echo(f"rapydo version: {__version__}")
        raise typer.Exit()


def controller_cli_options(
    ctx: typer.Context,
    project: str = typer.Option(
        None,
        "--project",
        "-p",
        help="Name of the project",
        callback=projectrc_values,
    ),
    # Deprecated since 2.1
    services_list: Optional[str] = typer.Option(
        None,
        "-s",
        help="Comma separated list of services to be included",
        callback=projectrc_values,
    ),
    hostname: str = typer.Option(
        "localhost",
        "--hostname",
        "-H",
        help="Hostname of the current machine",
        callback=projectrc_values,
        show_default=False,
    ),
    stack: str = typer.Option(
        None,
        "--stack",
        help="Docker-compose stack to be loaded",
        callback=projectrc_values,
    ),
    production: bool = typer.Option(
        False,
        "--production",
        "--prod",
        help="Enable production mode",
        callback=projectrc_values,
        show_default=False,
    ),
    testing: bool = typer.Option(
        False,
        "--testing",
        "--test",
        help="Enable test mode",
        callback=projectrc_values,
        envvar="TESTING",
        show_default=False,
    ),
    environment: List[str] = typer.Option(
        [],
        "--env",
        "-e",
        help="Temporary change the value of an environment variable",
    ),
    remote_engine: Optional[str] = typer.Option(
        None,
        "--remote",
        help="Execute commands on a remote host",
    ),
    no_backend: bool = typer.Option(
        False,
        "--no-backend",
        help="Exclude backend configuration",
        callback=projectrc_values,
        show_default=False,
    ),
    no_frontend: bool = typer.Option(
        False,
        "--no-frontend",
        help="Exclude frontend configuration",
        callback=projectrc_values,
        show_default=False,
    ),
    no_commons: bool = typer.Option(
        False,
        "--no-commons",
        help="Exclude project common configuration",
        callback=projectrc_values,
        show_default=False,
    ),
    version: bool = typer.Option(
        False,
        "--version",
        "-v",
        help="Print version information and quit",
        show_default=False,
        callback=version_callback,
        is_eager=True,
    ),
) -> None:

    # This is needed because during tests both Application and Configuration
    # are persistent and after a run (i.e. after starting the registry)
    # FORCE_COMPOSE_ENGINE remains enabled
    # It would not be needed during the normal use of the controller
    Configuration.FORCE_COMPOSE_ENGINE = False

    Configuration.set_action(ctx.invoked_subcommand, ctx.params)

    # Deprecated since 2.1
    if services_list:
        warnings.warn("-s option is going to be replaced by rapydo <command> service")
        time.sleep(1)

    Configuration.services_list = services_list
    Configuration.production = production
    Configuration.testing = testing
    Configuration.project = project
    Configuration.hostname = hostname
    Configuration.remote_engine = remote_engine
    Configuration.environment = {}
    for e in environment:

        if "=" not in e:
            print_and_exit("Invalid enviroment, missing value in {}", e)

        key, value = e.split("=")
        Configuration.environment[key] = value

    if stack:
        Configuration.stack = stack
    else:
        Configuration.stack = "production" if production else "development"

    Configuration.load_backend = not no_backend
    Configuration.load_frontend = not no_frontend
    Configuration.load_commons = not no_commons


# Temporary fix to ease migration to typer
class CommandsData:
    def __init__(
        self,
        files: List[Path],
        base_files: List[Path],
        services: List[str],
        active_services: List[str],
        base_services: ComposeServices,
        compose_config: ComposeServices,
    ):
        self.files = files
        self.base_files = base_files
        self.services = services
        self.active_services = active_services or []
        self.base_services = base_services
        self.compose_config = compose_config


class Application:

    # Typer app
    # Register callback with CLI options and basic initialization/checks
    app = typer.Typer(
        callback=controller_cli_options,
        context_settings={"help_option_names": ["--help", "-h"]},
    )
    # controller app
    controller: Optional["Application"] = None
    project_scaffold = Project()
    data: CommandsData
    gits: Dict[str, GitRepo] = {}
    env: Dict[str, EnvType] = {}

    base_services: ComposeServices
    compose_config: ComposeServices

    def __init__(self) -> None:

        Application.controller = self

        self.active_services: List[str] = []
        self.files: List[Path] = []
        self.base_files: List[Path] = []
        self.services = None
        self.enabled_services: List[str] = []
        load_commands()

        Application.load_projectrc()

    @staticmethod
    def serialize_parameter(
        param: str,
        value: CommandParameter,
        IF: CommandParameter = True,
    ) -> Optional[str]:

        if isinstance(value, enum.Enum):
            value = value.value

        if IF and value is not None:
            if isinstance(value, bool):
                return f"{param}"
            if isinstance(value, tuple) or isinstance(value, list):
                return " ".join([f"{param} {v}" for v in value])

            # Options => (--param value)
            if param:
                return f"{param} {value}"

            # Arguments ( => no param, only a value)
            return str(value)

        return None

    @staticmethod
    def print_command(*parameters: Optional[str]) -> None:

        pre_params = " ".join(
            [p for p in Configuration.parameters if p is not None]
        ).strip()
        post_params = " ".join([p for p in parameters if p is not None]).strip()

        if pre_params:
            pre_params = f"{pre_params} "

        if post_params:
            post_params = f" {post_params}"

        log.debug(
            "Command: rapydo {}{}{}",
            pre_params,
            Configuration.action,
            post_params,
            log_to_file=True,
        )

    @staticmethod
    def get_controller() -> "Application":
        if not Application.controller:  # pragma: no cover
            raise AttributeError("Application.controller not initialized")
        return Application.controller

    def controller_init(self, services: Optional[Iterable[str]] = None) -> None:
        if Configuration.create:
            Application.check_installed_software()
            return None

        main_folder_error = Application.project_scaffold.check_main_folder()

        if main_folder_error:
            print_and_exit(main_folder_error)

        if not Configuration.print_version:
            Application.check_installed_software()

        # if project is None, it is retrieve by project folder
        Configuration.project = Application.project_scaffold.get_project(
            Configuration.project
        )
        Configuration.ABS_PROJECT_PATH = PROJECT_DIR.joinpath(Configuration.project)

        if Configuration.print_version:
            self.read_specs(read_extended=True)
            return None

        log.debug("You are using RAPyDo version {}", __version__)
        if Configuration.check:
            log.info("Selected project: {}", Configuration.project)
        else:
            log.debug("Selected project: {}", Configuration.project)

        if (
            Configuration.initialize
            or Configuration.update
            or Configuration.check
            or Configuration.install
        ):
            Application.check_internet_connection()

        if Configuration.install:
            self.read_specs(read_extended=False)
            return None

        # Auth is not available yet, will be read by read_specs
        Application.project_scaffold.load_project_scaffold(
            Configuration.project, auth=None
        )
        Application.preliminary_version_check()

        # read project configuration
        self.read_specs(read_extended=True)

        # from read_specs
        Application.project_scaffold.load_frontend_scaffold(Configuration.frontend)
        Application.verify_rapydo_version()
        Application.project_scaffold.inspect_project_folder()

        self.current_uid = system.get_current_uid()
        self.current_gid = system.get_current_gid()

        # Cannot be tested
        if self.current_uid == ROOT_UID:  # pragma: no cover
            self.current_uid = BASE_UID
            log.warning("Current user is 'root'")
        else:
            os_user = system.get_username(self.current_uid)
            log.debug("Current UID: {} ({})", self.current_uid, os_user)
            log.debug("Current GID: {}", self.current_gid)

        if Configuration.initialize:
            return None

        Application.git_submodules()

        if Configuration.update:
            return None

        self.make_env()

        # Compose services and variables
        base_services, compose_config = self.get_compose_configuration(services)

        self.check_placeholders_and_passwords(compose_config, self.enabled_services)

        # Final step, launch the command

        Application.data = CommandsData(
            files=self.files,
            base_files=self.base_files,
            services=self.enabled_services,
            active_services=self.active_services,
            base_services=base_services,
            compose_config=compose_config,
        )

        return None

    @staticmethod
    def load_projectrc() -> None:

        projectrc_yaml = configuration.load_yaml_file(file=PROJECTRC, is_optional=True)

        Configuration.host_configuration = projectrc_yaml.pop(
            "project_configuration", {}
        )

        Configuration.projectrc = projectrc_yaml

    @staticmethod
    def check_installed_software() -> None:

        log.debug(
            "python version: {}.{}.{}",
            sys.version_info.major,
            sys.version_info.minor,
            sys.version_info.micro,
        )

        # Deprecated since 2.1
        if sys.version_info.major == 3 and sys.version_info.minor == 7:
            warnings.warn(
                YELLOW(
                    "Support for Python 3.7 is deprecated and will be dropped "
                    "in a future release. Please upgrade to python 3.8+"
                )
            )
            import time

            time.sleep(1)

        # 17.05 added support for multi-stage builds
        # https://docs.docker.com/compose/compose-file/compose-file-v3/#compose-and-docker-compatibility-matrix
        # 18.09.2 fixed the CVE-2019-5736 vulnerability
        # 20.10.0 introduced copy --chmod and improved logging
        Packages.check_program(
            "docker", min_version="20.10.0", min_recommended_version="20.10.0"
        )

        if docker.compose.is_installed():
            # too slow to verify the version on every commands... near half a seconds
            # Sometimes a couple of seconds!
            # v = docker.compose.version()
            # log.debug("docker compose is installed: {}", v)
            log.debug("docker compose is installed")
        else:  # pragma: no cover
            print_and_exit(
                "A mandatory dependency is missing: docker compose not found"
                "\nInstallation guide: "
                "https://docs.docker.com/compose/cli-command/#installing-compose-v2"
                "\nor try the automated installation with {command}",
                command=RED("rapydo install compose"),
            )

        # no need to check the git executable, because alredy verified by GitPython
        # in case of missing git GitPython will fail and this check will never executed
        # Packages.check_program("git")

    def read_specs(self, read_extended: bool = True) -> None:
        """Read project configuration"""

        try:

            confs = configuration.read_configuration(
                default_file_path=CONFS_DIR,
                base_project_path=Configuration.ABS_PROJECT_PATH,
                projects_path=PROJECT_DIR,
                submodules_path=SUBMODULES_DIR,
                read_extended=read_extended,
                production=Configuration.production,
            )
            Configuration.specs = configuration.mix_configuration(
                confs[0], Configuration.host_configuration
            )
            self.extended_project = confs[1]
            self.extended_project_path = confs[2]

        except AttributeError as e:  # pragma: no cover
            print_and_exit(str(e))

        Configuration.frontend = glom(
            Configuration.specs, "variables.env.FRONTEND_FRAMEWORK", default=NO_FRONTEND
        )

        if Configuration.frontend == NO_FRONTEND:
            Configuration.frontend = None

        Configuration.project_title = glom(
            Configuration.specs, "project.title", default="Unknown title"
        )
        Configuration.version = glom(Configuration.specs, "project.version", default="")
        Configuration.rapydo_version = glom(
            Configuration.specs, "project.rapydo", default=""
        )

        Configuration.project_description = glom(
            Configuration.specs, "project.description", default="Unknown description"
        )

        Configuration.project_keywords = glom(
            Configuration.specs, "project.keywords", default=""
        )

        if not Configuration.rapydo_version:  # pragma: no cover
            print_and_exit(
                "RAPyDo version not found in your project_configuration file"
            )

        Configuration.rapydo_version = str(Configuration.rapydo_version)

    @staticmethod
    def preliminary_version_check() -> None:

        specs = configuration.load_yaml_file(
            file=Configuration.ABS_PROJECT_PATH.joinpath(
                configuration.PROJECT_CONF_FILENAME
            )
        )

        Application.verify_rapydo_version(
            rapydo_version=glom(specs, "project.rapydo", default="")
        )

    @staticmethod
    def verify_rapydo_version(rapydo_version: str = "") -> bool:
        """
        Verify if the installed controller matches the current project requirement
        """

        if not rapydo_version:
            rapydo_version = Configuration.rapydo_version

        if not rapydo_version:  # pragma: no cover
            return True

        r = LooseVersion(rapydo_version)
        c = LooseVersion(__version__)
        if r == c:
            return True
        else:  # pragma: no cover
            if r > c:
                ac = f"Upgrade your controller to version {r}"
            else:
                ac = f"Downgrade your controller to version {r} or upgrade your project"

            msg = f"""RAPyDo version is not compatible.

This project requires rapydo {r}, you are using {c}. {ac}

You can use of one:
  -  rapydo install               (install in editable from submodules/do, if available)
  -  rapydo install --no-editable (install from pypi)

"""

            print_and_exit(msg)

    @staticmethod
    def check_internet_connection() -> None:
        """Check if connected to internet"""

        try:
            requests.get("https://www.google.com", timeout=2)
            if Configuration.check:
                log.info("Internet connection is available")
        except requests.ConnectionError:  # pragma: no cover
            print_and_exit("Internet connection is unavailable")

    @staticmethod
    def working_clone(
        name: str, repo: Dict[str, str], from_path: Optional[Path] = None
    ) -> Optional[GitRepo]:

        # substitute values starting with '$$'
        myvars = {
            ANGULAR: Configuration.frontend == ANGULAR,
        }

        condition = repo.get("if", "")
        if condition.startswith("$$"):
            # Is this repo enabled?
            if not myvars.get(condition.lstrip("$"), None):
                return None

        repo.setdefault(
            "branch",
            Configuration.rapydo_version
            if Configuration.rapydo_version
            else __version__,
        )

        if from_path is not None:

            local_path = from_path.joinpath(name)
            if not local_path.exists():
                print_and_exit("Submodule {} not found in {}", name, local_path)

            submodule_path = Path(SUBMODULES_DIR, name)

            if submodule_path.exists():
                log.info("Path {} already exists, removing", submodule_path)
                if submodule_path.is_dir() and not submodule_path.is_symlink():
                    shutil.rmtree(submodule_path)
                else:
                    submodule_path.unlink()

            os.symlink(local_path, submodule_path)

        url = cast(str, repo.get("online_url"))
        branch = cast(str, repo.get("branch"))
        return git.clone(
            url=url,
            path=Path(name),
            branch=branch,
            do=Configuration.initialize,
            check=not Configuration.install,
        )

    @staticmethod
    def git_submodules(from_path: Optional[Path] = None) -> None:
        """Check and/or clone git projects"""

        submodules: Dict[str, Dict[str, str]] = glom(
            Configuration.specs,
            "variables.submodules",
            default=cast(Dict[str, Dict[str, str]], {}),
        ).copy()

        main_repo = git.get_repo(".")
        # This is to reassure mypy, but this is check is already done
        # in preliminary checks, so it can never happen
        if not main_repo:  # pragma: no cover
            print_and_exit("Current folder is not a git main_repository")

        Application.gits["main"] = main_repo

        for name, submodule in submodules.items():
            repo = Application.working_clone(name, submodule, from_path=from_path)
            if repo:
                Application.gits[name] = repo

    def get_compose_configuration(
        self, enabled_services: Optional[Iterable[str]] = None
    ) -> Tuple[ComposeServices, ComposeServices]:

        compose_files: List[Path] = []

        MODE = f"{Configuration.stack}.yml"
        customconf = Configuration.ABS_PROJECT_PATH.joinpath(CONTAINERS_YAML_DIRNAME)
        angular_loaded = False

        def add(p: Path, f: str) -> None:
            compose_files.append(p.joinpath(f))

        if Configuration.load_backend:
            add(CONFS_DIR, "backend.yml")

        if Configuration.load_frontend:
            if Configuration.frontend == ANGULAR:
                add(CONFS_DIR, "angular.yml")
                angular_loaded = True
                if SWARM_MODE and Configuration.production:
                    add(CONFS_DIR, "swarm_angular_prod_options.yml")

        if SWARM_MODE and not Configuration.FORCE_COMPOSE_ENGINE:
            add(CONFS_DIR, "swarm_options.yml")

        if Application.env.get("NFS_HOST"):
            log.info("NFS Server is enabled")
            add(CONFS_DIR, "volumes_nfs.yml")
        else:
            add(CONFS_DIR, "volumes_local.yml")

        if Configuration.production:
            add(CONFS_DIR, "production.yml")
        else:
            add(CONFS_DIR, "development.yml")

            if angular_loaded:
                add(CONFS_DIR, "angular-development.yml")

        if self.extended_project and self.extended_project_path:
            extendedconf = self.extended_project_path.joinpath(CONTAINERS_YAML_DIRNAME)
            # Only added if exists, this is the only non mandatory conf file
            extended_mode_conf = extendedconf.joinpath(MODE)
            if extended_mode_conf.exists():
                compose_files.append(extended_mode_conf)

            if Configuration.load_commons:
                add(extendedconf, "commons.yml")

        if Configuration.load_commons:
            add(customconf, "commons.yml")

        add(customconf, MODE)

        # Read necessary files
        self.files, self.base_files = configuration.read_composer_yamls(compose_files)
        # to build the config with files and variables

        from controller.deploy.compose_v2 import Compose

        compose = Compose(files=self.base_files)
        base_services = compose.get_config().services

        compose = Compose(files=self.files)
        compose_config = compose.get_config().services

        self.active_services = services.find_active(compose_config)

        self.enabled_services = services.get_services(
            Configuration.services_list or enabled_services,
            default=self.active_services,
        )

        for service in self.enabled_services:
            if service not in self.active_services:
                print_and_exit("No such service: {}", service)

        log.debug("Enabled services: {}", self.enabled_services)

        self.create_datafile(list(compose_config.keys()), self.active_services)

        return base_services, compose_config

    def create_projectrc(self) -> None:
        templating = Templating()
        t = templating.get_template(
            "projectrc",
            {
                "project": Configuration.project,
                "hostname": Configuration.hostname,
                "swarm": SWARM_MODE,
                "production": Configuration.production,
                "testing": Configuration.testing,
                "services": self.active_services,
                "envs": Configuration.environment,
            },
        )
        templating.save_template(PROJECTRC, t, force=True)

        Application.load_projectrc()

        if not self.files:
            log.debug("Created temporary default {} file", PROJECTRC)
            PROJECTRC.unlink()
        else:
            log.info("Created default {} file", PROJECTRC)

    def make_env(self) -> None:

        try:
            COMPOSE_ENVIRONMENT_FILE.unlink()
        except FileNotFoundError:
            pass

        Application.env = glom(Configuration.specs, "variables.env", default={})

        Application.env["PROJECT_DOMAIN"] = Configuration.hostname
        Application.env["COMPOSE_PROJECT_NAME"] = Configuration.project

        Application.env["DATA_DIR"] = str(Path("data").resolve())
        Application.env["SUBMODULE_DIR"] = str(SUBMODULES_DIR.resolve())
        Application.env["PROJECT_DIR"] = str(
            PROJECT_DIR.joinpath(Configuration.project).resolve()
        )

        if self.extended_project_path is None:
            Application.env["BASE_PROJECT_DIR"] = Application.env["PROJECT_DIR"]
        else:
            Application.env["BASE_PROJECT_DIR"] = str(
                self.extended_project_path.resolve()
            )

        if self.extended_project is None:
            Application.env["EXTENDED_PROJECT"] = EXTENDED_PROJECT_DISABLED
            Application.env["BASE_PROJECT"] = Application.env["COMPOSE_PROJECT_NAME"]
        else:
            Application.env["EXTENDED_PROJECT"] = str(self.extended_project)
            Application.env["BASE_PROJECT"] = Application.env["EXTENDED_PROJECT"]

        Application.env["RAPYDO_VERSION"] = __version__
        Application.env["BUILD"] = git.get_last_commit(Application.gits["main"])
        Application.env["PROJECT_VERSION"] = Configuration.version
        Application.env["CURRENT_UID"] = str(self.current_uid)
        Application.env["CURRENT_GID"] = str(self.current_gid)
        Application.env["PROJECT_TITLE"] = (
            Configuration.project_title or "Unknown title"
        )
        Application.env["PROJECT_DESCRIPTION"] = (
            Configuration.project_description or "Unknown description"
        )
        Application.env["PROJECT_KEYWORDS"] = Configuration.project_keywords or ""

        if Configuration.testing and not Configuration.production:
            Application.env["APP_MODE"] = "test"

        Application.env["CELERYBEAT_SCHEDULER"] = services.get_celerybeat_scheduler(
            Application.env
        )

        if Configuration.load_frontend:
            if Configuration.frontend == ANGULAR:
                Application.env["ACTIVATE_ANGULAR"] = "1"

        services.check_rabbit_password(Application.env.get("RABBITMQ_PASSWORD"))
        services.check_redis_password(Application.env.get("REDIS_PASSWORD"))
        services.check_mongodb_password(Application.env.get("MONGO_PASSWORD"))

        for e in Application.env:
            env_value = os.environ.get(e)
            if env_value is None:
                continue
            Application.env[e] = env_value

        Application.env.update(Configuration.environment)

        if SWARM_MODE:

            if not Application.env.get("SWARM_MANAGER_ADDRESS"):
                Application.env["SWARM_MANAGER_ADDRESS"] = system.get_local_ip(
                    Configuration.production
                )

            if not Application.env.get("REGISTRY_HOST"):
                Application.env["REGISTRY_HOST"] = Application.env[
                    "SWARM_MANAGER_ADDRESS"
                ]

            # is None ensure empty string as a valid address
            if Application.env.get("SYSLOG_ADDRESS") is None:
                manager_addr = Application.env["SWARM_MANAGER_ADDRESS"]
                Application.env["SYSLOG_ADDRESS"] = f"tcp://{manager_addr}:514"

        if Configuration.FORCE_COMPOSE_ENGINE or not SWARM_MODE:
            DEPLOY_ENGINE = "compose"
        else:
            DEPLOY_ENGINE = "swarm"

        Application.env["DEPLOY_ENGINE"] = DEPLOY_ENGINE

        # Unfortunately this will only work after the creation of the network
        # i.e. will be fallen back to 127.0.0.1 the first time
        try:
            DOCKER_SUBNET = docker.network.inspect(
                f"{Configuration.project}_{DEPLOY_ENGINE}_default"
            ).ipam.config[0]["Subnet"]
        # The first execution will fail and fallen back to localhost
        except DockerException:
            DOCKER_SUBNET = "127.0.0.1"
        Application.env["DOCKER_SUBNET"] = DOCKER_SUBNET

        bool_envs = [
            # This variable is for RabbitManagement and is expected to be true|false
            "RABBITMQ_SSL_FAIL_IF_NO_PEER_CERT",
            # These variables are for Neo4j and are expected to be true|false
            "NEO4J_SSL_ENABLED",
            "NEO4J_ALLOW_UPGRADE",
            "NEO4J_RECOVERY_MODE",
        ]
        with open(COMPOSE_ENVIRONMENT_FILE, "w+") as whandle:
            for key, value in sorted(Application.env.items()):

                # Deprecated since 1.0
                # Backend and Frontend use different booleans due to Py vs Js
                # 0/1 is a much more portable value to prevent true|True|"true"
                # This fixes troubles in setting boolean values only used by Angular
                # (expected true|false) or used by Pyton (expected True|False)
                if key not in bool_envs:  # pragma: no cover
                    if isinstance(value, str):
                        if value.lower() == "true":
                            warnings.warn(
                                f"Deprecated value for {key}, convert {value} to 1",
                                DeprecationWarning,
                            )

                        if value.lower() == "false":
                            warnings.warn(
                                f"Deprecated value for {key}, convert {value} to 0",
                                DeprecationWarning,
                            )

                if value is None:
                    value = ""
                else:
                    value = str(value)
                if " " in value:
                    value = f"'{value}'"

                # if len(value) == 0:
                #     value = f"'{value}'"

                whandle.write(f"{key}={value}\n")

    @staticmethod
    def create_datafile(services: List[str], active_services: List[str]) -> None:
        try:
            DATAFILE.unlink()
        except FileNotFoundError:
            pass

        data = {
            "submodules": [k for k, v in Application.gits.items() if v is not None],
            "services": active_services,
            "allservices": services,
        }

        with open(DATAFILE, "w+") as outfile:
            json.dump(data, outfile)

    @staticmethod
    def parse_datafile(key: str) -> List[str]:
        try:
            with open(DATAFILE) as json_file:
                datafile = json.load(json_file)
                return cast(List[str], datafile.get(key, []))
        except FileNotFoundError:
            return []

    @staticmethod
    def autocomplete_service(
        ctx: click.core.Context, param: click.Parameter, incomplete: str
    ) -> List[str]:
        values = Application.parse_datafile("services")
        if not incomplete:
            return values
        return [x for x in values if x.startswith(incomplete)]

    @staticmethod
    def autocomplete_allservice(
        ctx: click.core.Context, param: click.Parameter, incomplete: str
    ) -> List[str]:
        values = Application.parse_datafile("allservices")
        if not incomplete:
            return values
        return [x for x in values if x.startswith(incomplete)]

    @staticmethod
    def autocomplete_submodule(
        ctx: click.core.Context, param: click.Parameter, incomplete: str
    ) -> List[str]:
        values = Application.parse_datafile("submodules")
        if not incomplete:
            return values
        return [x for x in values if x.startswith(incomplete)]

    @staticmethod
    def check_placeholders_and_passwords(
        compose_services: ComposeServices, active_services: List[str]
    ) -> None:

        if not active_services:  # pragma: no cover
            print_and_exit(
                """You have no active service
\nSuggestion: to activate a top-level service edit your project_configuration
and add the variable "ACTIVATE_DESIREDSERVICE: 1"
                """
            )
        elif Configuration.check:
            log.info("Active services: {}", active_services, log_to_file=True)

        extra_services: List[str] = []
        if SWARM_MODE and REGISTRY not in active_services:
            extra_services.append(REGISTRY)

        all_services = active_services + extra_services

        missing: Dict[str, Set[str]] = {}
        passwords: Dict[str, str] = {}
        passwords_services: Dict[str, Set[str]] = {}
        for service_name in all_services:
            # This can happens with `rapydo run swagger` because in case of run
            # the controller_init method is executed without passing the service
            # This is because interfaces are not enabled on the base stack and the
            # controller_init([service]) would fail
            # As side effect, non-existing services are not blocked
            if service_name not in compose_services:
                continue

            service = compose_services[service_name]

            if service:
                for key, value in service.environment.items():
                    if str(value) == PLACEHOLDER:
                        key = services.normalize_placeholder_variable(key)
                        missing.setdefault(key, set())
                        missing[key].add(service_name)

                    elif key.endswith("_PASSWORD") and value:
                        key = services.normalize_placeholder_variable(key)
                        passwords.setdefault(key, value)
                        passwords_services.setdefault(key, set())
                        passwords_services[key].add(service_name)

        placeholders = []
        for variable, raw_services in missing.items():

            serv = services.vars_to_services_mapping.get(variable) or raw_services
            active_serv = [s for s in serv if s in all_services]

            if active_serv:
                placeholders.append([variable, ", ".join(active_serv)])

        MIN_PASSWORD_SCORE = int(
            Application.env.get("MIN_PASSWORD_SCORE", 2)  # type: ignore
        )
        for variable, raw_services in passwords_services.items():

            serv = services.vars_to_services_mapping.get(variable) or raw_services
            active_serv = [s for s in serv if s in all_services]
            if active_serv:
                password = passwords.get(variable)
                result = zxcvbn(password)
                score = result["score"]
                if score < MIN_PASSWORD_SCORE:
                    if score == MIN_PASSWORD_SCORE - 1:
                        log.warning("The password used in {} is weak", variable)
                    elif score == MIN_PASSWORD_SCORE - 2:
                        log.error("The password used in {} is very weak", variable)
                    else:
                        log.critical(
                            "The password used in {} is extremely weak", variable
                        )

        if placeholders:
            log.critical("The following variables are missing in your configuration:")

            print("")
            print(
                tabulate(
                    placeholders,
                    tablefmt=TABLE_FORMAT,
                    headers=["VARIABLE", "SERVICE(S)"],
                )
            )
            print("")

            log.info("You can fix this error by updating your .projectrc file")

            sys.exit(1)

        return None

    @staticmethod
    def git_update(ignore_submodule: List[str]) -> None:

        for name, gitobj in Application.gits.items():
            if name in ignore_submodule:
                log.debug("Skipping update on {}", name)
                continue

            if gitobj and not git.can_be_updated(name, gitobj):
                print_and_exit("Can't continue with updates")

        controller_is_updated = False
        for name, gitobj in Application.gits.items():
            if name in ignore_submodule:
                continue

            if name == "do":
                controller_is_updated = True

            if gitobj:
                git.update(name, gitobj)

        if controller_is_updated:
            installation_path = Packages.get_installation_path("rapydo")

            # Can't be tested on GA since rapydo is alway installed from a folder
            if not installation_path:  # pragma: no cover
                log.warning(
                    "Controller is not installed in editable mode, "
                    "rapydo is unable to update it"
                )

            elif Application.gits["do"].working_dir:
                do_dir = Path(Application.gits["do"].working_dir)
                if do_dir.is_symlink():
                    do_dir = do_dir.resolve()
                    # This can be used starting from python 3.9
                    # do_dir = do_dir.readlink()

                if do_dir == installation_path:
                    log.info(
                        "Controller installed from {} and updated", installation_path
                    )
                else:
                    log.warning(
                        "Controller not updated because it is installed outside this "
                        "project. Installation path is {}, the current folder is {}",
                        installation_path,
                        do_dir,
                    )
            else:  # pragma: no cover
                log.warning("Controller submodule folder can't be found")

    @staticmethod
    def git_checks(ignore_submodule: List[str]) -> None:

        for name, gitobj in Application.gits.items():
            if name in ignore_submodule:
                log.debug("Skipping checks on {}", name)
                continue
            if gitobj:
                git.check_updates(name, gitobj)
                git.check_unstaged(name, gitobj)
