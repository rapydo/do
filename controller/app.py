import os
import shutil
import sys
from collections import OrderedDict  # can be removed from python 3.7
from distutils.version import LooseVersion

import requests
import typer
from glom import glom

from controller import (
    COMPOSE_ENVIRONMENT_FILE,
    CONFS_DIR,
    CONTAINERS_YAML_DIRNAME,
    EXTENDED_PROJECT_DISABLED,
    PLACEHOLDER,
    PROJECT_DIR,
    PROJECTRC,
    SUBMODULES_DIR,
    TESTING,
    __version__,
    gitter,
    log,
)
from controller.commands import load_commands
from controller.compose import Compose
from controller.packages import Packages
from controller.project import ANGULAR, NO_FRONTEND, REACT, Project
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
        if ctx.resilient_parsing:
            return

        if value != param.get_default(ctx):
            return value

        from_projectrc = Configuration.projectrc.get(param.name)

        if from_projectrc is not None:
            return from_projectrc

        return value


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
        version=None,
        rapydo_version=None,
        conf_vars=None,
        compose_config=None,
        services_dict=None,
        template_builds=None,
        builds=None,
        gits=None,
    ):
        self.files = files
        self.base_files = base_files
        self.services = services
        self.services_list = services_list
        self.active_services = active_services
        self.base_services = base_services
        self.version = version
        self.rapydo_version = rapydo_version
        self.conf_vars = conf_vars
        self.compose_config = compose_config
        self.services_dict = services_dict
        self.template_builds = template_builds
        self.builds = builds
        self.gits = gits


class Application:

    # typer app
    app = None
    # controller app
    controller = None
    project_scaffold = Project()

    def __init__(self):

        Application.controller = self

        self.tested_connection = False
        self.rapydo_version = None  # To be retrieved from projet_configuration
        self.project_title = None  # To be retrieved from projet_configuration
        self.project_description = None  # To be retrieved from projet_configuration
        self.version = None
        self.active_services = None
        self.specs = None
        self.vars = None
        self.files = None
        self.base_files = None
        self.services = None
        self.base_services = None
        self.services_dict = None
        self.compose_config = None
        self.template_builds = None
        self.builds = None
        self.gits = OrderedDict()

        # Register callback with CLI options and basic initialization/checks
        Application.app = typer.Typer(
            callback=self.controller_init,
            context_settings={"help_option_names": ["--help", "-h"]},
        )

        load_commands()

    def controller_init(
        self,
        ctx: typer.Context,
        project: str = typer.Option(
            None,
            "--project",
            "-p",
            help="Name of the project",
            callback=Configuration.projectrc_values,
        ),
        services_list: str = typer.Option(
            None,
            "--services",
            "-s",
            help="Comma separated list of services",
            callback=Configuration.projectrc_values,
        ),
        hostname: str = typer.Option(
            "localhost",
            "--hostname",
            "-H",
            help="Hostname of the current machine",
            callback=Configuration.projectrc_values,
            show_default=False,
        ),
        stack: str = typer.Option(
            None,
            "--stack",
            help="Docker-compose stack to be loaded",
            callback=Configuration.projectrc_values,
        ),
        production: bool = typer.Option(
            False,
            "--production",
            "--prod",
            help="Enable production mode",
            callback=Configuration.projectrc_values,
            show_default=False,
        ),
        privileged: bool = typer.Option(
            False,
            "--privileged",
            help="Allow containers privileged mode",
            callback=Configuration.projectrc_values,
            show_default=False,
        ),
        no_backend: bool = typer.Option(
            False,
            "--no-backend",
            help="Exclude backend configuration",
            callback=Configuration.projectrc_values,
            show_default=False,
        ),
        no_frontend: bool = typer.Option(
            False,
            "--no-frontend",
            help="Exclude frontend configuration",
            callback=Configuration.projectrc_values,
            show_default=False,
        ),
        no_commons: bool = typer.Option(
            False,
            "--no-commons",
            help="Exclude project common configuration",
            callback=Configuration.projectrc_values,
            show_default=False,
        ),
    ):

        Configuration.set_action(ctx.invoked_subcommand)

        Configuration.production = production
        Configuration.privileged = privileged
        Configuration.project = project
        Configuration.hostname = hostname

        if stack:
            Configuration.stack = stack
        else:
            Configuration.stack = "production" if production else "development"

        Configuration.load_backend = not no_backend
        Configuration.load_frontend = not no_frontend
        Configuration.load_commons = not no_commons

        Application.load_projectrc()

        if Configuration.create:
            self.check_installed_software()
            return True

        current_folder = os.getcwd()
        err = Application.project_scaffold.find_main_folder()

        if err is not None:
            os.chdir(current_folder)
            log.exit(err)

        if Configuration.print_version:
            # from inside project folder, load configuration
            (
                Configuration.project,
                self.ABS_PROJECT_PATH,
            ) = Application.project_scaffold.get_project(Configuration.project)
            self.read_specs()

            Application.data = CommandsData(
                version=self.version, rapydo_version=self.rapydo_version,
            )

            return True

        log.debug("You are using RAPyDo version {}", __version__)

        self.check_installed_software()

        # TODO: give an option to skip things when you are not connected
        if (
            Configuration.initialize
            or Configuration.update
            or Configuration.check
            or Configuration.install
        ):
            self.check_internet_connection()

        if Configuration.install:
            (
                Configuration.project,
                self.ABS_PROJECT_PATH,
            ) = Application.project_scaffold.get_project(Configuration.project)
            self.read_specs()

            Application.data = CommandsData(
                rapydo_version=self.rapydo_version, gits=self.gits,
            )

            return True

        # if project is None, it is retrieve by project folder
        (
            Configuration.project,
            self.ABS_PROJECT_PATH,
        ) = Application.project_scaffold.get_project(Configuration.project)
        self.checked("Selected project: {}", Configuration.project)
        # Auth is not yet available, will be read by read_specs
        Application.project_scaffold.load_project_scaffold(
            Configuration.project, auth=None
        )
        self.preliminary_version_check()

        self.read_specs()  # read project configuration

        # from read_specs
        Application.project_scaffold.load_frontend_scaffold(Configuration.frontend)
        self.verify_rapydo_version()
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

            enabled_services = services.get_services(
                services_list, default=self.active_services
            )

            Application.data = CommandsData(
                files=self.files,
                base_files=self.base_files,
                services=enabled_services,
                services_list=services_list,
                active_services=self.active_services,
                base_services=self.base_services,
                version=self.version,
                rapydo_version=self.rapydo_version,
                conf_vars=self.vars,
                compose_config=self.compose_config,
                services_dict=self.services_dict,
                template_builds=self.template_builds,
                builds=self.builds,
                gits=self.gits,
            )
            return True

        self.git_submodules()

        if Configuration.update:

            enabled_services = services.get_services(
                services_list, default=self.active_services
            )

            Application.data = CommandsData(
                files=self.files,
                base_files=self.base_files,
                services=enabled_services,
                services_list=services_list,
                active_services=self.active_services,
                base_services=self.base_services,
                version=self.version,
                rapydo_version=self.rapydo_version,
                conf_vars=self.vars,
                compose_config=self.compose_config,
                services_dict=self.services_dict,
                template_builds=self.template_builds,
                builds=self.builds,
                gits=self.gits,
            )
            return True

        self.make_env()

        # Compose services and variables
        self.read_composers()
        self.set_active_services()

        self.check_placeholders()

        # Final step, launch the command
        enabled_services = services.get_services(
            services_list, default=self.active_services
        )

        Application.data = CommandsData(
            files=self.files,
            base_files=self.base_files,
            services=enabled_services,
            services_list=services_list,
            active_services=self.active_services,
            base_services=self.base_services,
            version=self.version,
            rapydo_version=self.rapydo_version,
            conf_vars=self.vars,
            compose_config=self.compose_config,
            services_dict=self.services_dict,
            template_builds=self.template_builds,
            builds=self.builds,
            gits=self.gits,
        )

        return True

    @staticmethod
    def load_projectrc():
        Configuration.projectrc = configuration.load_yaml_file(
            PROJECTRC, path=os.curdir, is_optional=True
        )
        Configuration.host_configuration = Configuration.projectrc.pop(
            "project_configuration", {}
        )

    def checked(self, message, *args, **kws):
        if Configuration.check:
            log.info(message, *args, **kws)
        else:
            log.verbose(message, *args, **kws)

    def check_installed_software(self):

        self.checked(
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

    def read_specs(self):
        """ Read project configuration """

        try:
            if Configuration.initialize:
                read_extended = False
            elif Configuration.install:
                read_extended = False
            else:
                read_extended = True

            confs = configuration.read_configuration(
                default_file_path=CONFS_DIR,
                base_project_path=self.ABS_PROJECT_PATH,
                projects_path=PROJECT_DIR,
                submodules_path=SUBMODULES_DIR,
                read_extended=read_extended,
                production=Configuration.production,
            )
            self.specs = confs[0]
            self.extended_project = confs[1]
            self.extended_project_path = confs[2]

            self.specs = configuration.mix_configuration(
                self.specs, Configuration.host_configuration
            )

        except AttributeError as e:  # pragma: no cover
            log.exit(e)

        self.vars = self.specs.get("variables", {})

        log.verbose("Configuration loaded")

        Configuration.frontend = glom(
            self.vars, "env.FRONTEND_FRAMEWORK", default=NO_FRONTEND
        )

        if Configuration.frontend == NO_FRONTEND:
            Configuration.frontend = None

        if Configuration.frontend is not None:
            log.verbose("Frontend framework: {}", Configuration.frontend)

        self.project_title = glom(self.specs, "project.title", default="Unknown title")
        self.version = glom(self.specs, "project.version", default=None)
        self.rapydo_version = glom(self.specs, "project.rapydo", default=None)
        self.project_description = glom(
            self.specs, "project.description", default="Unknown description"
        )

        if self.rapydo_version is None:  # pragma: no cover
            log.exit("RAPyDo version not found in your project_configuration file")

    def preliminary_version_check(self):

        specs = configuration.load_yaml_file(
            file=configuration.PROJECT_CONF_FILENAME,
            path=self.ABS_PROJECT_PATH,
            keep_order=True,
        )
        v = glom(specs, "project.rapydo", default=None)

        self.verify_rapydo_version(rapydo_version=v)

    def verify_rapydo_version(self, rapydo_version=None):
        """
        If your project requires a specific rapydo version, check if you are
        the rapydo-controller matching that version
        """

        if rapydo_version is None:
            rapydo_version = self.rapydo_version

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

    def check_internet_connection(self):
        """ Check if connected to internet """

        try:
            requests.get("https://www.google.com")
        except requests.ConnectionError:  # pragma: no cover
            log.exit("Internet connection is unavailable")
        else:
            self.checked("Internet connection is available")
            self.tested_connection = True

    def working_clone(self, name, repo, from_path=None):

        # substitute values starting with '$$'
        myvars = {
            ANGULAR: Configuration.frontend == ANGULAR,
            REACT: Configuration.frontend == REACT,
        }
        repo = services.apply_variables(repo, myvars)

        # Is this single repo enabled?
        repo_enabled = repo.pop("if", False)
        if not repo_enabled:
            return None

        repo["do"] = Configuration.initialize
        repo["check"] = not Configuration.install
        repo.setdefault("path", name)
        repo.setdefault(
            "branch", self.rapydo_version if self.rapydo_version else __version__
        )

        if from_path is not None:

            local_path = os.path.join(from_path, repo["path"])
            if not os.path.exists(local_path):
                log.exit("Submodule {} not found in {}", repo["path"], local_path)

            submodule_path = os.path.join(os.curdir, SUBMODULES_DIR, repo["path"])

            if os.path.exists(submodule_path):
                log.info("Path {} already exists, removing", submodule_path)
                if os.path.isdir(submodule_path) and not os.path.islink(submodule_path):
                    shutil.rmtree(submodule_path)
                else:
                    os.remove(submodule_path)

            os.symlink(local_path, submodule_path)

        return gitter.clone(**repo)

    def git_submodules(self, from_path=None):
        """ Check and/or clone git projects """

        repos = self.vars.get("submodules", {}).copy()

        self.gits["main"] = gitter.get_repo(".")

        for name, repo in repos.items():
            self.gits[name] = self.working_clone(name, repo, from_path=from_path)

    def set_active_services(self):
        self.services_dict, self.active_services = services.find_active(
            self.compose_config
        )

    def read_composers(self):

        # Find configuration that tells us which files have to be read

        # substitute values starting with '$$'

        myvars = {
            "backend": Configuration.load_backend,
            ANGULAR: Configuration.frontend == ANGULAR and Configuration.load_frontend,
            REACT: Configuration.frontend == REACT and Configuration.load_frontend,
            "commons": Configuration.load_commons,
            "extended-commons": self.extended_project is not None
            and Configuration.load_commons,
            "mode": f"{Configuration.stack}.yml",
            "extended-mode": self.extended_project is not None,
            "baseconf": CONFS_DIR,
            "customconf": os.path.join(self.ABS_PROJECT_PATH, CONTAINERS_YAML_DIRNAME),
        }

        if self.extended_project_path is None:
            myvars["extendedproject"] = None
        else:
            myvars["extendedproject"] = os.path.join(
                self.extended_project_path, CONTAINERS_YAML_DIRNAME
            )

        compose_files = OrderedDict()

        confs = self.vars.get("composers", {})
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
                "testing": TESTING,
                "services": self.active_services,
            },
        )
        templating.save_template(PROJECTRC, t, force=True)

        Application.load_projectrc()

        if self.active_services is None:
            log.debug("Created temporary default {} file", PROJECTRC)
            os.remove(PROJECTRC)
        else:
            log.info("Created default {} file", PROJECTRC)
        self.read_specs()

    def make_env(self):
        envfile = os.path.join(os.curdir, COMPOSE_ENVIRONMENT_FILE)

        try:
            os.unlink(envfile)
            log.verbose("Removed cache of {}", COMPOSE_ENVIRONMENT_FILE)
        except FileNotFoundError:
            pass

        env = self.vars.get("env", {})
        env["PROJECT_DOMAIN"] = Configuration.hostname
        env["COMPOSE_PROJECT_NAME"] = Configuration.project
        env["VANILLA_DIR"] = os.path.abspath(os.curdir)
        env["SUBMODULE_DIR"] = os.path.join(env["VANILLA_DIR"], SUBMODULES_DIR)
        env["PROJECT_DIR"] = os.path.join(
            env["VANILLA_DIR"], PROJECT_DIR, Configuration.project
        )

        if self.extended_project_path is None:
            env["EXTENDED_PROJECT_PATH"] = env["PROJECT_DIR"]
        else:
            env["EXTENDED_PROJECT_PATH"] = os.path.join(
                env["VANILLA_DIR"], self.extended_project_path
            )

        if self.extended_project is None:
            env["EXTENDED_PROJECT"] = EXTENDED_PROJECT_DISABLED
        else:
            env["EXTENDED_PROJECT"] = self.extended_project

        env["RAPYDO_VERSION"] = __version__
        env["PROJECT_VERSION"] = self.version
        env["CURRENT_UID"] = self.current_uid
        env["CURRENT_GID"] = self.current_gid
        env["PROJECT_TITLE"] = self.project_title
        env["PROJECT_DESCRIPTION"] = self.project_description
        env["DOCKER_PRIVILEGED_MODE"] = "true" if Configuration.privileged else "false"

        env["CELERYBEAT_SCHEDULER"] = services.get_celerybeat_scheduler(env)

        env["DOCKER_NETWORK_MODE"] = "bridge"

        services.check_rabbit_password(env.get("RABBITMQ_PASSWORD"))

        with open(envfile, "w+") as whandle:
            for key, value in sorted(env.items()):
                if value is None:
                    value = ""
                else:
                    value = str(value)
                if " " in value:
                    value = f"'{value}'"
                whandle.write(f"{key}={value}\n")
            log.verbose("Created {} file", COMPOSE_ENVIRONMENT_FILE)

    def check_placeholders(self):

        if len(self.active_services) == 0:  # pragma: no cover
            log.exit(
                """You have no active service
\nSuggestion: to activate a top-level service edit your project_configuration
and add the variable "ACTIVATE_DESIREDSERVICE: 1"
                """
            )
        else:
            self.checked("Active services: {}", self.active_services)

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
                log.exit(
                    "Missing variable: {}. Cannot find a service mapping this variable",
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
            m = "\n".join(placeholders)
            tips = "\n\nYou can fix this error by updating the "
            tips += "project_configuration.yaml file or your local .projectrc file\n"
            log.exit(
                "The following variables are missing in your configuration:\n\n{}{}",
                m,
                tips,
            )

        else:
            log.verbose("No placeholder variable to be replaced")

        return missing

    @staticmethod
    def git_update(ignore_submodule, gits):

        for name, gitobj in gits.items():
            if name in ignore_submodule:
                log.debug("Skipping update on {}", name)
                continue
            if gitobj is None:
                continue
            gitter.update(name, gitobj)

    @staticmethod
    def git_checks(ignore_submodule, gits):

        for name, gitobj in gits.items():
            if name in ignore_submodule:
                log.debug("Skipping checks on {}", name)
                continue
            if gitobj is None:
                continue

            gitter.check_updates(name, gitobj)
            gitter.check_unstaged(name, gitobj)
