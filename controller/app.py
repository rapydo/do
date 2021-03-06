import json
import os
import shutil
import sys
import warnings
from collections import OrderedDict  # can be removed from python 3.7
from distutils.version import LooseVersion
from pathlib import Path
from typing import Any, Dict, List, MutableMapping, Optional, Set, Union, cast

import requests
import typer
from glom import glom

from controller import (
    COMPOSE_ENVIRONMENT_FILE,
    CONFS_DIR,
    CONTAINERS_YAML_DIRNAME,
    DATAFILE,
    EXTENDED_PROJECT_DISABLED,
    PLACEHOLDER,
    PROJECT_DIR,
    PROJECTRC,
    SUBMODULES_DIR,
    __version__,
    gitter,
    log,
)
from controller.commands import load_commands
from controller.compose import Compose
from controller.packages import Packages
from controller.project import ANGULAR, NO_FRONTEND, Project
from controller.templating import Templating
from controller.utilities import configuration, services, system

warnings.simplefilter("always", DeprecationWarning)

DataFileStub = Dict[str, List[str]]

ROOT_UID = 0
BASE_UID = 1000


class Configuration:
    projectrc: Dict[str, str] = {}
    # To be better characterized. This is a:
    # {'variables': 'env': Dict[str, str]}
    host_configuration: Dict[str, Dict[str, Dict[str, str]]] = {}
    specs: MutableMapping[str, str] = OrderedDict()
    services_list: Optional[str]
    excluded_services_list: Optional[str]
    environment: Dict[str, str]

    action: Optional[str] = None

    production: bool = False
    testing: bool = False
    privileged: bool = False
    project: str = ""
    frontend: Optional[str] = None
    hostname: str = ""
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

    @staticmethod
    def set_action(action: Optional[str]) -> None:
        Configuration.action = action
        Configuration.initialize = Configuration.action == "init"
        Configuration.update = Configuration.action == "update"
        Configuration.check = Configuration.action == "check"
        Configuration.install = Configuration.action == "install"
        Configuration.print_version = Configuration.action == "version"
        Configuration.create = Configuration.action == "create"


def projectrc_values(
    ctx: typer.Context, param: typer.CallbackParam, value: str
) -> Optional[str]:
    if ctx.resilient_parsing:  # pragma: no cover
        return None

    if value != param.get_default(ctx):
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
    services_list: Optional[str] = typer.Option(
        None,
        "--services",
        "-s",
        help="Comma separated list of services to be included",
        callback=projectrc_values,
    ),
    excluded_services_list: Optional[str] = typer.Option(
        None,
        "--skip-services",
        "-S",
        help="Comma separated list of services to be exluded",
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
        "",
        "--env",
        "-e",
        help="Temporary change the value of an environment variable",
    ),
    privileged: bool = typer.Option(
        False,
        "--privileged",
        help="Allow containers privileged mode",
        callback=projectrc_values,
        show_default=False,
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

    Configuration.set_action(ctx.invoked_subcommand)

    if services_list and excluded_services_list:
        Application.exit(
            "Incompatibile use of both --services/-s and --skip-services/-S options"
        )

    Configuration.services_list = services_list
    Configuration.excluded_services_list = excluded_services_list
    Configuration.production = production
    Configuration.testing = testing
    Configuration.privileged = privileged
    Configuration.project = project
    Configuration.hostname = hostname
    Configuration.environment = {}
    for e in environment:
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
        files: List[Path] = [],
        base_files: List[Path] = [],
        services: List[str] = [],
        active_services: List[str] = [],
        base_services: List[Any] = [],
        compose_config: List[Any] = [],
        services_dict: Dict[str, Any] = None,
    ):
        self.files = files
        self.base_files = base_files
        self.services = services
        self.active_services = active_services or []
        self.base_services = base_services
        self.compose_config = compose_config
        self.services_dict = services_dict or {}


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
    data = CommandsData()
    gits: MutableMapping[str, gitter.GitRepoType] = OrderedDict()

    def __init__(self) -> None:

        Application.controller = self

        self.active_services: List[str] = []
        self.files: List[Path] = []
        self.base_files: List[Path] = []
        self.services = None
        self.enabled_services: List[str] = []
        self.base_services: List[Any] = []
        self.compose_config: List[Any] = []
        self.services_dict: Dict[str, List[Any]] = {}

        load_commands()

        Application.load_projectrc()

    @staticmethod
    def exit(message: str, *args: Union[str, Path], **kwargs: Union[str, Path]) -> None:
        log.critical(message, *args, **kwargs)
        sys.exit(1)

    @staticmethod
    def get_controller() -> "Application":
        if not Application.controller:  # pragma: no cover
            raise AttributeError("Application.controller not initialized")
        return Application.controller

    def controller_init(self, read_extended: bool = True) -> None:
        if Configuration.create:
            Application.check_installed_software()
            return None

        main_folder_error = Application.project_scaffold.check_main_folder()

        if main_folder_error:
            Application.exit(main_folder_error)

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

        # TODO: give an option to skip things when you are not connected
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

        # Auth is not yet available, will be read by read_specs
        Application.project_scaffold.load_project_scaffold(
            Configuration.project, auth=None
        )
        Application.preliminary_version_check()

        self.read_specs(read_extended=read_extended)  # read project configuration

        # from read_specs
        Application.project_scaffold.load_frontend_scaffold(Configuration.frontend)
        Application.verify_rapydo_version()
        Application.project_scaffold.inspect_project_folder()

        # get user launching rapydo commands
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
        self.read_composers()
        self.set_active_services()

        self.check_placeholders()

        # Final step, launch the command

        Application.data = CommandsData(
            files=self.files,
            base_files=self.base_files,
            services=self.enabled_services,
            active_services=self.active_services,
            base_services=self.base_services,
            compose_config=self.compose_config,
            services_dict=self.services_dict,
        )

        return None

    @staticmethod
    def load_projectrc() -> None:

        projectrc_yaml = configuration.load_yaml_file(
            PROJECTRC, path=Path(), is_optional=True
        )

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

        if sys.version_info.major == 3 and sys.version_info.minor == 6:
            # Deprecated since 1.2
            log.warning(
                "Support to python 3.6 is deprecated and will be dropped "
                "in the next version, please upgrade to python 3.7+"
            )

        # 17.05 added support for multi-stage builds
        # https://docs.docker.com/compose/compose-file/compose-file-v3/#compose-and-docker-compatibility-matrix
        Packages.check_program(
            "docker", min_version="17.05", min_recommended_version="19.03.8"
        )
        Packages.check_program("git")

        # Check for CVE-2019-5736 vulnerability
        Packages.check_docker_vulnerability()

        Packages.check_python_package("compose", min_version="1.18")
        Packages.check_python_package("docker", min_version="4.0.0")
        Packages.check_python_package("requests", min_version="2.6.1")
        Packages.check_python_package("pip", min_version="10.0.0")

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
            Application.exit(str(e))

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
            Application.exit(
                "RAPyDo version not found in your project_configuration file"
            )

        Configuration.rapydo_version = str(Configuration.rapydo_version)

    @staticmethod
    def preliminary_version_check() -> None:

        specs = configuration.load_yaml_file(
            file=configuration.PROJECT_CONF_FILENAME,
            path=Configuration.ABS_PROJECT_PATH,
            keep_order=True,
        )

        Application.verify_rapydo_version(
            rapydo_version=glom(specs, "project.rapydo", default="")
        )

    @staticmethod
    def verify_rapydo_version(rapydo_version: str = "") -> bool:
        """
        Verify if the installed rapydo version matches the current project requirement
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

            log.critical(msg)
            sys.exit(1)

    @staticmethod
    def check_internet_connection() -> None:
        """Check if connected to internet"""

        try:
            requests.get("https://www.google.com")
            if Configuration.check:
                log.info("Internet connection is available")
        except requests.ConnectionError:  # pragma: no cover
            Application.exit("Internet connection is unavailable")

    # from_path: Optional[Path]
    @staticmethod
    def working_clone(name, repo, from_path=None):

        # substitute values starting with '$$'
        myvars = {
            ANGULAR: Configuration.frontend == ANGULAR,
        }
        repo = services.apply_variables(repo, myvars)

        # Is this single repo enabled?
        if not repo.pop("if", True):
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
                Application.exit("Submodule {} not found in {}", name, local_path)

            submodule_path = Path(SUBMODULES_DIR, name)

            if submodule_path.exists():
                log.info("Path {} already exists, removing", submodule_path)
                if submodule_path.is_dir() and not submodule_path.is_symlink():
                    shutil.rmtree(submodule_path)
                else:
                    submodule_path.unlink()

            os.symlink(local_path, submodule_path)

        return gitter.clone(
            url=repo.get("online_url"),
            path=name,
            branch=repo.get("branch"),
            do=Configuration.initialize,
            check=not Configuration.install,
        )

    @staticmethod
    def git_submodules(from_path: Optional[Path] = None) -> None:
        """Check and/or clone git projects"""

        repos: Dict[str, str] = glom(
            Configuration.specs,
            "variables.submodules",
            default=cast(Dict[str, str], {}),
        ).copy()
        Application.gits["main"] = gitter.get_repo(".")

        for name, repo in repos.items():
            Application.gits[name] = Application.working_clone(
                name, repo, from_path=from_path
            )

    def set_active_services(self) -> None:
        self.services_dict, self.active_services = services.find_active(
            self.compose_config
        )

        self.enabled_services = services.get_services(
            Configuration.services_list,
            Configuration.excluded_services_list,
            default=self.active_services,
        )

        log.debug("Enabled services: {}", self.enabled_services)

        self.create_datafile()

    def read_composers(self) -> None:

        # Find configuration that tells us which files have to be read

        # substitute values starting with '$$'

        myvars = {
            "backend": Configuration.load_backend,
            ANGULAR: Configuration.frontend == ANGULAR and Configuration.load_frontend,
            "commons": Configuration.load_commons,
            "extended-commons": self.extended_project is not None
            and Configuration.load_commons,
            "mode": f"{Configuration.stack}.yml",
            "extended-mode": self.extended_project is not None,
            "baseconf": CONFS_DIR,
            "customconf": Configuration.ABS_PROJECT_PATH.joinpath(
                CONTAINERS_YAML_DIRNAME
            ),
        }

        if self.extended_project_path is None:
            myvars["extendedproject"] = None
        else:
            myvars["extendedproject"] = self.extended_project_path.joinpath(
                CONTAINERS_YAML_DIRNAME
            )

        compose_files = OrderedDict()

        confs: Dict[str, Any] = glom(
            Configuration.specs, "variables.composers", default={}
        )
        for name, conf in confs.items():
            compose_files[name] = services.apply_variables(conf, myvars)

        # Read necessary files
        self.files, self.base_files = configuration.read_composer_yamls(compose_files)

        # to build the config with files and variables
        dc = Compose(files=self.base_files)
        self.base_services = dc.config()

        dc = Compose(files=self.files)
        self.compose_config = dc.config()

    def create_projectrc(self) -> None:
        templating = Templating()
        t = templating.get_template(
            "projectrc",
            {
                "project": Configuration.project,
                "hostname": Configuration.hostname,
                "production": Configuration.production,
                "testing": Configuration.testing,
                "services": self.active_services,
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

        env: Dict[str, Any] = glom(Configuration.specs, "variables.env", default={})

        env["PROJECT_DOMAIN"] = Configuration.hostname
        env["COMPOSE_PROJECT_NAME"] = Configuration.project
        env["VANILLA_DIR"] = Path().cwd()
        env["SUBMODULE_DIR"] = SUBMODULES_DIR.resolve()
        env["PROJECT_DIR"] = PROJECT_DIR.joinpath(Configuration.project).resolve()

        if self.extended_project_path is None:
            env["BASE_PROJECT_DIR"] = env["PROJECT_DIR"]
        else:
            env["BASE_PROJECT_DIR"] = self.extended_project_path.resolve()

        if self.extended_project is None:
            env["EXTENDED_PROJECT"] = EXTENDED_PROJECT_DISABLED
            env["BASE_PROJECT"] = env["COMPOSE_PROJECT_NAME"]
        else:
            env["EXTENDED_PROJECT"] = self.extended_project
            env["BASE_PROJECT"] = env["EXTENDED_PROJECT"]

        env["RAPYDO_VERSION"] = __version__
        env["PROJECT_VERSION"] = Configuration.version
        env["CURRENT_UID"] = self.current_uid
        env["CURRENT_GID"] = self.current_gid
        env["PROJECT_TITLE"] = Configuration.project_title
        env["PROJECT_DESCRIPTION"] = Configuration.project_description
        env["PROJECT_KEYWORDS"] = Configuration.project_keywords
        env["DOCKER_PRIVILEGED_MODE"] = "true" if Configuration.privileged else "false"

        if Configuration.testing:
            env["APP_MODE"] = "test"

        env["CELERYBEAT_SCHEDULER"] = services.get_celerybeat_scheduler(env)

        env["DOCKER_NETWORK_MODE"] = "bridge"

        services.check_rabbit_password(env.get("RABBITMQ_PASSWORD"))
        services.check_redis_password(env.get("REDIS_PASSWORD"))
        services.check_mongodb_password(env.get("MONGO_PASSWORD"))

        for e in env:
            env_value = os.environ.get(e)
            if env_value is None:
                continue
            env[e] = env_value

        env.update(Configuration.environment)

        bool_envs = [
            # This variable is for docker-compose and is expected to be true|false
            "DOCKER_PRIVILEGED_MODE",
            # This variable is for RabbitManagement and is expected to be true|false
            "RABBITMQ_SSL_FAIL_IF_NO_PEER_CERT",
            # These variables are for Neo4j and are expected to be true|false
            "NEO4J_SSL_ENABLED",
            "NEO4J_ALLOW_UPGRADE",
            "NEO4J_RECOVERY_MODE",
        ]
        with open(COMPOSE_ENVIRONMENT_FILE, "w+") as whandle:
            for key, value in sorted(env.items()):

                if (
                    Configuration.production
                    and key.endswith("_PASSWORD")
                    and value
                    and len(value) < 8
                ):
                    log.warning("{} is set with a short password", key)

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
                    elif isinstance(value, bool):
                        if value:
                            warnings.warn(
                                f"Deprecated value for {key}, convert {value} to 1",
                                DeprecationWarning,
                            )
                        else:
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
                whandle.write(f"{key}={value}\n")

    def create_datafile(self) -> None:
        try:
            DATAFILE.unlink()
        except FileNotFoundError:
            pass

        data: DataFileStub = {
            "submodules": [k for k, v in Application.gits.items() if v is not None],
            "services": self.active_services,
            "allservices": list(self.services_dict.keys()),
        }

        with open(DATAFILE, "w+") as outfile:
            json.dump(data, outfile)

    @staticmethod
    def parse_datafile() -> DataFileStub:
        output: DataFileStub = {}
        try:
            with open(DATAFILE) as json_file:
                datafile = json.load(json_file)
                # This is needed to let mypy understand the correct type
                output["submodules"] = datafile.get("submodules")
                output["services"] = datafile.get("services")
                output["allservices"] = datafile.get("allservices")
                return output
        except FileNotFoundError:
            return output

    @staticmethod
    def autocomplete_service(incomplete: str) -> List[str]:
        d = Application.parse_datafile()
        if not d:
            return []
        values = d.get("services", [])
        if not incomplete:
            return values
        return [x for x in values if x.startswith(incomplete)]

    @staticmethod
    def autocomplete_allservice(incomplete: str) -> List[str]:
        d = Application.parse_datafile()
        if not d:
            return []
        values = d.get("allservices", [])
        if not incomplete:
            return values
        return [x for x in values if x.startswith(incomplete)]

    @staticmethod
    def autocomplete_submodule(incomplete: str) -> List[str]:
        d = Application.parse_datafile()
        if not d:
            return []
        values = d.get("submodules", [])
        if not incomplete:
            return values
        return [x for x in values if x.startswith(incomplete)]

    def check_placeholders(self) -> Set[str]:

        if len(self.active_services) == 0:  # pragma: no cover
            Application.exit(
                """You have no active service
\nSuggestion: to activate a top-level service edit your project_configuration
and add the variable "ACTIVATE_DESIREDSERVICE: 1"
                """
            )
        elif Configuration.check:
            log.info("Active services: {}", self.active_services)

        missing = set()
        for service_name in self.active_services:
            service = self.services_dict.get(service_name)

            if service:
                for key, value in (
                    cast(Dict[str, Any], service).get("environment", {}).items()
                ):
                    if PLACEHOLDER in str(value):
                        key = services.normalize_placeholder_variable(key)
                        missing.add(key)

        placeholders = []
        for key in missing:

            serv = services.vars_to_services_mapping.get(key)

            if serv:
                active_serv = []
                for i in serv:
                    if i in self.active_services:
                        active_serv.append(i)

                if active_serv:
                    placeholders.append(
                        "{:<20}\trequired by\t{}".format(key, ", ".join(active_serv))
                    )
            # Should never happens since all services are configured, cannot be tested
            else:  # pragma: no cover
                # with py39 it would be key.removeprefix('INJECT_')
                if key.startswith("INJECT_"):
                    key = key[len("INJECT_") :]

                Application.exit(
                    "Missing variable: {}: cannot find a service mapping this variable",
                    key,
                )

        if len(placeholders) > 0:
            Application.exit(
                "The following variables are missing in your configuration:\n\n{}"
                "\n\nYou can fix this error by updating your .projectrc file\n",
                "\n".join(placeholders),
            )

        return missing

    @staticmethod
    def git_update(ignore_submodule: List[str]) -> None:

        for name, gitobj in Application.gits.items():
            if name in ignore_submodule:
                log.debug("Skipping update on {}", name)
                continue

            if gitobj and not gitter.can_be_updated(name, gitobj):
                Application.exit("Can't continue with updates")

        controller_is_updated = False
        for name, gitobj in Application.gits.items():
            if name in ignore_submodule:
                continue

            if name == "do":
                controller_is_updated = True

            if gitobj:
                gitter.update(name, gitobj)

        if controller_is_updated:
            installation_path = Packages.get_installation_path("rapydo")
            if installation_path:
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
            # Can't be tested on GA since rapydo is alway installed from a folder
            else:  # pragma: no cover
                log.warning(
                    "Controller is not installed in editable mode, "
                    "rapydo is unable to update it"
                )

    @staticmethod
    def git_checks(ignore_submodule: List[str]) -> None:

        for name, gitobj in Application.gits.items():
            if name in ignore_submodule:
                log.debug("Skipping checks on {}", name)
                continue
            if gitobj:
                gitter.check_updates(name, gitobj)
                gitter.check_unstaged(name, gitobj)
