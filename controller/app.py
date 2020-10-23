import json
import os
import shutil
import sys
from collections import OrderedDict  # can be removed from python 3.7
from distutils.version import LooseVersion
from pathlib import Path
from typing import List

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

ROOT_UID = 0
BASE_UID = 1000


# Old implementation
# # This is a second level parameter
# if isinstance(value, dict):
#     if key not in parse_conf["subcommands"]:
#         log.exit("Unknown command {} found in {}", key, PROJECTRC)
#     else:
#         conf = parse_conf["subcommands"][key]["suboptions"]
#         for subkey, subvalue in value.items():
#             if subkey in conf:
#                 conf[subkey]["default"] = subvalue
#             else:
#                 log.exit(
#                     "Unknown parameter {}/{} found in {}",
#                     key,
#                     subkey,
#                     PROJECTRC,
#                 )
# else:
#     # This is a first level option
#     if key in parse_conf["options"]:
#         parse_conf["options"][key]["default"] = value
#         parse_conf["options"][key]["projectrc"] = True
#     else:
#         log.exit("Unknown parameter {} found in {}", key, PROJECTRC)


class Configuration:
    projectrc = {}
    host_configuration = {}
    action = None

    production = False
    testing = False
    privileged = False
    project = None
    frontend = None
    hostname = None
    stack = None
    load_backend = False
    load_frontend = False
    load_commons = False

    def set_action(action):
        Configuration.action = action
        Configuration.initialize = Configuration.action == "init"
        Configuration.update = Configuration.action == "update"
        Configuration.check = Configuration.action == "check"
        Configuration.install = Configuration.action == "install"
        Configuration.print_version = Configuration.action == "version"
        Configuration.create = Configuration.action == "create"


def projectrc_values(ctx: typer.Context, param: typer.CallbackParam, value):
    if ctx.resilient_parsing:  # pragma: no cover
        return

    if value != param.get_default(ctx):
        return value

    from_projectrc = Configuration.projectrc.get(param.name)

    if from_projectrc is not None:
        return from_projectrc

    return value


def version_callback(value: bool):
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
    services_list: str = typer.Option(
        None,
        "--services",
        "-s",
        help="Comma separated list of services",
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
):

    Configuration.set_action(ctx.invoked_subcommand)

    Configuration.services_list = services_list
    Configuration.production = production
    Configuration.testing = testing
    Configuration.privileged = privileged
    Configuration.project = project
    Configuration.hostname = hostname
    Configuration.environment = [e.split("=") for e in environment]

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
        files=None,
        base_files=None,
        services=None,
        services_list=None,
        active_services=None,
        base_services=None,
        compose_config=None,
        services_dict=None,
    ):
        self.files = files
        self.base_files = base_files
        self.services = services
        self.services_list = services_list
        self.active_services = active_services
        self.base_services = base_services
        self.compose_config = compose_config
        self.services_dict = services_dict


class Application:

    # typer app
    app = None
    # controller app
    controller = None
    project_scaffold = Project()
    data = CommandsData()
    gits = OrderedDict()

    def __init__(self):

        Application.controller = self

        self.active_services = None
        self.files = None
        self.base_files = None
        self.services = None
        self.enabled_services = None
        self.base_services = None
        self.services_dict = None
        self.compose_config = None

        # Register callback with CLI options and basic initialization/checks
        Application.app = typer.Typer(
            callback=controller_cli_options,
            context_settings={"help_option_names": ["--help", "-h"]},
        )

        load_commands()

        Application.load_projectrc()

    def controller_init(self, read_extended=True):
        if Configuration.create:
            Application.check_installed_software()
            return True

        main_folder_error = Application.project_scaffold.check_main_folder()

        if main_folder_error:
            log.exit(main_folder_error)

        if not Configuration.print_version:
            Application.check_installed_software()

        # if project is None, it is retrieve by project folder
        Configuration.project = Application.project_scaffold.get_project(
            Configuration.project
        )
        Configuration.ABS_PROJECT_PATH = PROJECT_DIR.joinpath(Configuration.project)

        if Configuration.print_version:
            self.read_specs(read_extended=True)
            return True

        log.debug("You are using RAPyDo version {}", __version__)
        Application.checked("Selected project: {}", Configuration.project)

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
            return True

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
            self.current_os_user = "privileged"
            log.warning("Current user is 'root'")
        else:
            self.current_os_user = system.get_username(self.current_uid)
            log.debug(
                "Current user: {} (UID: {})", self.current_os_user, self.current_uid
            )
            log.debug("Current group ID: {}", self.current_gid)

        if Configuration.initialize:
            return True

        Application.git_submodules()

        if Configuration.update:
            return True

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
            services_list=Configuration.services_list,
            active_services=self.active_services,
            base_services=self.base_services,
            compose_config=self.compose_config,
            services_dict=self.services_dict,
        )

        return True

    @staticmethod
    def load_projectrc():
        Configuration.projectrc = configuration.load_yaml_file(
            PROJECTRC, path=Path(), is_optional=True
        )
        Configuration.host_configuration = Configuration.projectrc.pop(
            "project_configuration", {}
        )

    @staticmethod
    def checked(message, *args, **kws):
        if Configuration.check:
            log.info(message, *args, **kws)
        else:
            log.verbose(message, *args, **kws)

    @staticmethod
    def check_installed_software():

        Application.checked(
            "python version: {}.{}.{}",
            sys.version_info.major,
            sys.version_info.minor,
            sys.version_info.micro,
        )

        # 17.05 added support for multi-stage builds
        Packages.check_program("docker", min_version="17.05")
        Packages.check_program("git")

        # Check for CVE-2019-5736 vulnerability
        Packages.check_docker_vulnerability()

        Packages.check_python_package("compose", min_version="1.18")
        Packages.check_python_package("docker", min_version="4.0.0")
        Packages.check_python_package("requests", min_version="2.6.1")
        Packages.check_python_package("pip", min_version="10.0.0")

    def read_specs(self, read_extended=True):
        """ Read project configuration """

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
            log.exit(e)

        log.verbose("Configuration loaded")

        Configuration.frontend = glom(
            Configuration.specs, "variables.env.FRONTEND_FRAMEWORK", default=NO_FRONTEND
        )

        if Configuration.frontend == NO_FRONTEND:
            Configuration.frontend = None

        if Configuration.frontend is not None:
            log.verbose("Frontend framework: {}", Configuration.frontend)

        Configuration.project_title = glom(
            Configuration.specs, "project.title", default="Unknown title"
        )
        Configuration.version = glom(
            Configuration.specs, "project.version", default=None
        )
        Configuration.rapydo_version = str(
            glom(Configuration.specs, "project.rapydo", default=None)
        )
        Configuration.project_description = glom(
            Configuration.specs, "project.description", default="Unknown description"
        )

        if Configuration.rapydo_version is None:  # pragma: no cover
            log.exit("RAPyDo version not found in your project_configuration file")

    @staticmethod
    def preliminary_version_check():

        specs = configuration.load_yaml_file(
            file=configuration.PROJECT_CONF_FILENAME,
            path=Configuration.ABS_PROJECT_PATH,
            keep_order=True,
        )

        Application.verify_rapydo_version(
            rapydo_version=glom(specs, "project.rapydo", default=None)
        )

    @staticmethod
    def verify_rapydo_version(rapydo_version=None):
        """
        Verify if the installed rapydo version matches the current project requirement
        """

        if rapydo_version is None:
            rapydo_version = Configuration.rapydo_version

        if rapydo_version is None:  # pragma: no cover
            return True

        r = LooseVersion(rapydo_version)
        c = LooseVersion(__version__)
        if r == c:
            return True
        else:  # pragma: no cover
            if r > c:
                action = f"Upgrade your controller to version {r}"
            else:
                action = f"Downgrade your controller to version {r}"
                action += " or upgrade your project"

            msg = "RAPyDo version is not compatible\n\n"
            msg += "This project requires rapydo {}, you are using {}\n\n{}\n".format(
                r, c, action
            )

            log.exit(msg)

    @staticmethod
    def check_internet_connection():
        """ Check if connected to internet """

        try:
            requests.get("https://www.google.com")
            Application.checked("Internet connection is available")
        except requests.ConnectionError:  # pragma: no cover
            log.exit("Internet connection is unavailable")

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
                log.exit("Submodule {} not found in {}", name, local_path)

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
    def git_submodules(from_path=None):
        """ Check and/or clone git projects """

        repos = glom(Configuration.specs, "variables.submodules", default={}).copy()
        Application.gits["main"] = gitter.get_repo(".")

        for name, repo in repos.items():
            Application.gits[name] = Application.working_clone(
                name, repo, from_path=from_path
            )

    def set_active_services(self):
        self.services_dict, self.active_services = services.find_active(
            self.compose_config
        )

        self.enabled_services = services.get_services(
            Configuration.services_list, default=self.active_services
        )

        self.create_datafile()

    def read_composers(self):

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

        confs = glom(Configuration.specs, "variables.composers", default={})
        for name, conf in confs.items():
            compose_files[name] = services.apply_variables(conf, myvars)

        # Read necessary files
        self.files, self.base_files = configuration.read_composer_yamls(compose_files)

        # to build the config with files and variables
        dc = Compose(files=self.base_files)
        self.base_services = dc.config()

        dc = Compose(files=self.files)
        self.compose_config = dc.config()

        log.verbose("Configuration order:\n{}", self.files)

    def create_projectrc(self):
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

        if self.active_services is None:
            log.debug("Created temporary default {} file", PROJECTRC)
            PROJECTRC.unlink()
        else:
            log.info("Created default {} file", PROJECTRC)

    def make_env(self):

        try:
            COMPOSE_ENVIRONMENT_FILE.unlink()
            log.verbose("Removed cache of {}", COMPOSE_ENVIRONMENT_FILE)
        except FileNotFoundError:
            pass

        env = glom(Configuration.specs, "variables.env", default={})

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
        env["DOCKER_PRIVILEGED_MODE"] = "true" if Configuration.privileged else "false"

        if Configuration.testing:
            env["APP_MODE"] = "test"

        env["CELERYBEAT_SCHEDULER"] = services.get_celerybeat_scheduler(env)

        env["DOCKER_NETWORK_MODE"] = "bridge"

        services.check_rabbit_password(env.get("RABBITMQ_PASSWORD"))

        for e in env:
            env_value = os.environ.get(e)
            if env_value is None:
                continue
            env[e] = env_value

        for key, value in Configuration.environment:
            env[key] = value

        with open(COMPOSE_ENVIRONMENT_FILE, "w+") as whandle:
            for key, value in sorted(env.items()):
                if value is None:
                    value = ""
                else:
                    value = str(value)
                if " " in value:
                    value = f"'{value}'"
                whandle.write(f"{key}={value}\n")
            log.verbose("Created {} file", COMPOSE_ENVIRONMENT_FILE)

    def create_datafile(self):
        try:
            DATAFILE.unlink()
            log.verbose("Removed data cache")
        except FileNotFoundError:
            pass

        data = {
            "submodules": [k for k, v in Application.gits.items() if v is not None],
            "services": self.active_services,
            "allservices": list(self.services_dict.keys()),
            "interfaces": self.get_available_interfaces(),
        }

        with open(DATAFILE, "w+") as outfile:
            json.dump(data, outfile)

    @staticmethod
    def parse_datafile():
        try:
            with open(DATAFILE) as json_file:
                return json.load(json_file)
        except FileNotFoundError:
            return {}

    @staticmethod
    def autocomplete_service(incomplete: str):
        d = Application.parse_datafile()
        if not d:
            return []
        values = d.get("services", [])
        if not incomplete:
            return values
        return [x for x in values if x.startswith(incomplete)]

    def get_available_interfaces(self):
        available_interfaces = list()
        for s in self.compose_config:
            name = s.get("name", "")
            if name.endswith("ui"):
                available_interfaces.append(name[0:-2])
        return available_interfaces

    @staticmethod
    def autocomplete_interfaces(incomplete: str):
        d = Application.parse_datafile()
        if not d:
            return []
        values = d.get("interfaces", [])
        if not incomplete:
            return values
        return [x for x in values if x.startswith(incomplete)]

    @staticmethod
    def autocomplete_allservice(incomplete: str):
        d = Application.parse_datafile()
        if not d:
            return []
        values = d.get("allservices", [])
        if not incomplete:
            return values
        return [x for x in values if x.startswith(incomplete)]

    @staticmethod
    def autocomplete_submodule(incomplete: str):
        d = Application.parse_datafile()
        if not d:
            return []
        values = d.get("submodules", [])
        if not incomplete:
            return values
        return [x for x in values if x.startswith(incomplete)]

    def check_placeholders(self):

        if len(self.active_services) == 0:  # pragma: no cover
            log.exit(
                """You have no active service
\nSuggestion: to activate a top-level service edit your project_configuration
and add the variable "ACTIVATE_DESIREDSERVICE: 1"
                """
            )
        else:
            Application.checked("Active services: {}", self.active_services)

        missing = set()
        for service_name in self.active_services:
            service = self.services_dict.get(service_name)

            for key, value in service.get("environment", {}).items():
                if PLACEHOLDER in str(value):
                    key = services.normalize_placeholder_variable(key)
                    missing.add(key)

        placeholders = []
        for key in missing:

            serv = services.vars_to_services_mapping.get(key)
            # Should never happens since all services are configured, cannot be tested
            if not serv:  # pragma: no cover

                # with py39 it would be key.removeprefix('INJECT_')
                if key.startswith("INJECT_"):
                    key = key[len("INJECT_") :]

                log.exit(
                    "Missing variable: {}: cannot find a service mapping this variable",
                    key,
                )

            active_serv = []
            for i in serv:
                if i in self.active_services:
                    active_serv.append(i)
            if len(active_serv) > 0:
                placeholders.append(
                    "{:<20}\trequired by\t{}".format(key, ", ".join(active_serv))
                )
            else:
                log.verbose(
                    "Variable {} is missing, but {} service(s) not active", key, serv
                )

        if len(placeholders) > 0:
            log.exit(
                "The following variables are missing in your configuration:\n\n{}"
                "\n\nYou can fix this error by updating the your .projectrc file\n",
                "\n".join(placeholders),
            )

        log.verbose("No placeholder variable to be replaced")

        return missing

    @staticmethod
    def git_update(ignore_submodule):

        for name, gitobj in Application.gits.items():
            if name in ignore_submodule:
                log.debug("Skipping update on {}", name)
                continue
            if gitobj:
                gitter.update(name, gitobj)

    @staticmethod
    def git_checks(ignore_submodule):

        for name, gitobj in Application.gits.items():
            if name in ignore_submodule:
                log.debug("Skipping checks on {}", name)
                continue
            if gitobj:
                gitter.check_updates(name, gitobj)
                gitter.check_unstaged(name, gitobj)
