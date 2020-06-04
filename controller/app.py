# -*- coding: utf-8 -*-

import os
import sys
import time
import shutil
import urllib3
import requests
import importlib
from distutils.version import LooseVersion
from collections import OrderedDict
from datetime import datetime
from glom import glom
from plumbum.commands.processes import ProcessExecutionError

from controller import TESTING
from controller import PROJECT_DIR, EXTENDED_PROJECT_DISABLED, CONTAINERS_YAML_DIRNAME
from controller import __version__
from controller.commands import version as version_cmd
from controller.commands import install as install_cmd
from controller.commands import create as create_cmd
from controller.project import Project, NO_FRONTEND, ANGULAR, REACT
from controller.utilities import services
from controller.utilities import system
from controller.utilities import configuration
from controller import gitter
from controller import COMPOSE_ENVIRONMENT_FILE, PLACEHOLDER
from controller import SUBMODULES_DIR, CONFS_DIR, PROJECTRC
from controller.compose import Compose
from controller.templating import Templating
from controller import log

ROOT_UID = 0
BASE_UID = 1000


class Application:

    """
    Main application class

    It handles all implemented commands defined in `argparser.yaml`
    """

    def __init__(self, arguments):

        self.arguments = arguments
        self.current_args = self.arguments.current_args
        self.project_scaffold = Project()
        self.tested_connection = False
        self.rapydo_version = None  # To be retrieved from projet_configuration
        self.project_title = None  # To be retrieved from projet_configuration
        self.project_description = None  # To be retrieved from projet_configuration
        self.version = None
        self.active_services = None
        self.specs = None
        self.vars = None
        self.hostname = None
        self.files = None
        self.base_files = None
        self.services = None
        self.frontend = None
        self.base_services = None
        self.services_dict = None
        self.compose_config = None
        self.template_builds = None
        self.builds = None
        self.gits = OrderedDict()
        self.get_args()

        if self.create:
            self.check_installed_software()
            create_cmd.__call__(
                args=self.current_args,
                project=self.project,
                project_scaffold=self.project_scaffold,
            )
            sys.exit(0)

        err = self.project_scaffold.find_main_folder()

        if self.print_version:
            # from inside project folder, load configuration
            self.project, self.ABS_PROJECT_PATH = self.project_scaffold.get_project(
                self.project
            )
            if err is None:
                self.read_specs()
            version_cmd.__call__(
                project=self.project,
                version=self.version,
                rapydo_version=self.rapydo_version,
            )
            sys.exit(0)

        if err is not None:
            log.exit(err)

        log.debug("You are using RAPyDo version {}", __version__)

        self.check_installed_software()

        # TODO: give an option to skip things when you are not connected
        if self.initialize or self.update or self.check or self.install:
            self.check_internet_connection()

        if self.install:
            self.project, self.ABS_PROJECT_PATH = self.project_scaffold.get_project(
                self.project
            )
            self.read_specs()
            self.git_submodules()
            install_cmd.__call__(
                args=self.current_args,
                gits=self.gits,
                rapydo_version=self.rapydo_version,
            )
            sys.exit(0)

        # if project is None, it is retrieve by project folder
        self.project, self.ABS_PROJECT_PATH = self.project_scaffold.get_project(
            self.project
        )
        self.current_args['project'] = self.project
        self.checked("Selected project: {}", self.project)
        # Auth is not yet available, will be read by read_specs
        self.project_scaffold.load_project_scaffold(self.project, auth=None)
        self.preliminary_version_check()

        self.read_specs()  # read project configuration
        self.hostname = self.current_args.get('hostname', 'localhost')

        # from read_specs
        self.project_scaffold.load_frontend_scaffold(self.frontend)
        self.verify_rapydo_version()
        self.project_scaffold.inspect_project_folder()
        # will be set to True if init and projectrc is missing or forced
        force_projectrc_creation = False

        # get user launching rapydo commands
        self.current_uid = system.get_current_uid()
        self.current_gid = system.get_current_gid()
        # Cannot be tested
        if self.current_uid == ROOT_UID:  # pragma: no cover
            self.current_uid = BASE_UID
            self.current_os_user = 'privileged'
            skip_check_perm = True
            log.warning("Current user is 'root'")
        else:
            self.current_os_user = system.get_username(self.current_uid)
            skip_check_perm = not self.current_args.get('check_permissions', False)
            log.debug(
                "Current user: {} (UID: {})", self.current_os_user, self.current_uid
            )
            log.debug(
                "Current group ID: {}", self.current_gid
            )

        if not skip_check_perm:
            self.inspect_permissions()

        try:
            argname = next(iter(self.arguments.remaining_args))
        except StopIteration:
            pass
        else:
            log.exit("Unknown argument:'{}'.\nUse --help to list options", argname)

        # Verify if we implemented the requested command
        cmd_name = self.action.replace("-", "_")
        # Deprecated since 0.7.3
        if cmd_name == 'ssl_certificate':
            log.warning("Deprecated command, use rapydo ssl instead")

            time.sleep(1)
            cmd_name = 'ssl'
        try:
            command = importlib.import_module("controller.commands.{}".format(cmd_name))
        # enable me after dropping python 3.5
        # except ModuleNotFoundError:
        except BaseException as e:
            log.error(e)
            log.exit("Command not found: {}", self.action)

        if not hasattr(command, "__call__"):
            log.exit("Command not implemented: {}", self.action)

        if self.initialize:

            if self.current_args.get('force', False):
                force_projectrc_creation = True
            else:
                force_projectrc_creation = not self.arguments.projectrc and \
                    not self.arguments.host_configuration

            # We have to create the .projectrc twice
            # One generic here with main options and another after the complete
            # conf reading to set services variables
            if force_projectrc_creation:
                self.create_projectrc()

        self.git_submodules()

        if self.update:
            self.git_checks_or_update()
            # Reading again the configuration, it may change with git updates
            self.read_specs()
        elif self.check:
            if self.current_args.get('no_git', False):
                log.info("Skipping git checks")
            else:
                log.info("Checking git (skip with --no-git)")
                self.git_checks_or_update()

        self.make_env()

        # Compose services and variables
        self.read_composers()
        self.services_dict, self.active_services = services.find_active(
            self.compose_config
        )
        # We have to create the .projectrc twice
        # One generic with main options and another here
        # when services are available to set specific configurations
        if force_projectrc_creation:
            self.create_projectrc()
            # Read again! :-(
            self.make_env()
            self.read_composers()
            self.services_dict, self.active_services = services.find_active(
                self.compose_config
            )

        self.check_placeholders()

        if self.tested_connection:

            self.check_time()

        # Final step, launch the command
        enabled_services = self.get_services(default=self.active_services)
        command.__call__(
            args=self.current_args,
            specs=self.specs,
            arguments=self.arguments,
            files=self.files,
            base_files=self.base_files,
            services=enabled_services,
            active_services=self.active_services,
            base_services=self.base_services,
            project=self.project,
            version=self.version,
            rapydo_version=self.rapydo_version,
            hostname=self.hostname,
            production=self.production,
            frontend=self.frontend,
            conf_vars=self.vars,
            compose_config=self.compose_config,
            services_dict=self.services_dict,
            template_builds=self.template_builds,
            builds=self.builds,
            gits=self.gits,
            project_scaffold=self.project_scaffold,
        )

    def checked(self, message, *args, **kws):
        if self.action == "check":
            log.info(message, *args, **kws)
        else:
            log.verbose(message, *args, **kws)

    def get_args(self):

        # Action
        self.action = self.current_args.get('action')
        if self.action is None:
            log.exit("Internal misconfiguration")

        # Action aliases
        self.initialize = self.action == 'init'
        self.update = self.action == 'update'
        self.start = self.action == 'start'
        self.check = self.action == 'check'
        self.install = self.action == 'install'
        self.print_version = self.action == 'version'
        self.pull = self.action == 'pull'
        self.create = self.action == 'create'

        # Others
        self.production = self.current_args.get('production', False)
        self.project = self.current_args.get('project')

        if self.project is not None:
            if "_" in self.project:
                suggest = "\nPlease consider to rename {} into {}".format(
                    self.project,
                    self.project.replace("_", ""),
                )
                log.exit("Wrong project name, _ is not a valid character.{}", suggest)

            if self.project in self.project_scaffold.reserved_project_names:
                log.exit(
                    "You selected a reserved name, invalid project name: {}",
                    self.project
                )

    def check_installed_software(self):

        # Python 3.5 deprecated since 0.7.3
        # EOL expected 2020-09-13 (~ rapydo 0.7.6?)
        # https://devguide.python.org/#status-of-python-branches
        if sys.version_info < (3, 6):
            log.warning(
                "You are using pyton {}.{}.{}, please consider to upgrade "
                "before reaching End Of Life (expected in September 2020)",
                sys.version_info.major,
                sys.version_info.minor,
                sys.version_info.micro
            )
        else:
            self.checked(
                "python version: {}.{}.{}",
                sys.version_info.major,
                sys.version_info.minor,
                sys.version_info.micro
            )
        # Check if docker is installed
        # 17.05 added support for multi-stage builds
        self.check_program('docker', min_version="17.05")

        # Check for CVE-2019-5736 vulnerability
        # Checking version of docker server, since docker client is not affected
        # and the two versions can differ
        v = Application.get_bin_version(
            'docker', option=["version", "--format", "'{{.Server.Version}}'"])

        if v is None:
            log.exit("No docker installation found, cannot continue")

        safe_version = "18.09.2"
        if LooseVersion(safe_version) > LooseVersion(v):
            log.critical(
                """Your docker version is vulnerable to CVE-2019-5736

***************************************************************************************
Your docker installation (version {}) is affected by a critical vulnerability
that allows specially-crafted containers to gain administrative privileges on the host.
For details please visit: https://cve.mitre.org/cgi-bin/cvename.cgi?name=CVE-2019-5736
***************************************************************************************
To fix this issue, please update docker to version {}+
            """,
                v,
                safe_version,
            )

        # Check docker-compose version
        self.check_python_package('compose', min_version="1.18")
        self.check_python_package('docker', min_version="2.6.1")
        self.check_python_package('requests', min_version="2.6.1")
        self.check_python_package('pip', min_version="10.0.0")

        # Check if git is installed
        self.check_program('git')  # , max_version='2.14.3')

    def check_program(self, program, min_version=None, max_version=None):

        found_version = Application.get_bin_version(program)
        if found_version is None:

            hints = ""

            if program == "docker":
                hints = "To install docker visit: https://get.docker.com"

            if len(hints) > 0:
                hints = "\n\n{}".format(hints)

            log.exit("Missing requirement: '{}' not found.{}", program, hints)
        if min_version is not None:
            if LooseVersion(min_version) > LooseVersion(found_version):
                version_error = "Minimum supported version for {} is {}".format(
                    program,
                    min_version,
                )
                version_error += ", found {} ".format(found_version)
                log.exit(version_error)

        if max_version is not None:
            if LooseVersion(max_version) < LooseVersion(found_version):
                version_error = "Maximum supported version for {} is {}".format(
                    program,
                    max_version,
                )
                version_error += ", found {} ".format(found_version)
                log.exit(version_error)

        self.checked("{} version: {}", program, found_version)

    def check_python_package(self, package_name, min_version=None, max_version=None):

        # BEWARE: to not import this package outside the function
        # Otherwise pip will go crazy
        # (we cannot understand why, but it does!)
        from controller.packages import package_version

        found_version = package_version(package_name)
        if found_version is None:
            log.exit("Could not find the following python package: {}", package_name)
        try:
            if min_version is not None:
                if LooseVersion(min_version) > LooseVersion(found_version):
                    version_error = "Minimum supported version for {} is {}".format(
                        package_name, min_version)
                    version_error += ", found {} ".format(found_version)
                    log.exit(version_error)

            if max_version is not None:
                if LooseVersion(max_version) < LooseVersion(found_version):
                    version_error = "Maximum supported version for {} is {}".format(
                        package_name, max_version)
                    version_error += ", found {} ".format(found_version)
                    log.exit(version_error)

            self.checked("{} version: {}", package_name, found_version)
        except TypeError as e:
            log.error("{}: {}", e, found_version)

    @staticmethod
    def path_is_readable(filepath):
        return (os.path.isfile(filepath) or os.path.isdir(filepath)) and os.access(
            filepath, os.R_OK
        )

    @staticmethod
    def path_is_writable(filepath):
        return (os.path.isfile(filepath) or os.path.isdir(filepath)) and os.access(
            filepath, os.W_OK
        )

    def check_permissions(self, path):

        # if os.path.islink(path):
        #     log.warning("Skipping checks on {} (symbolic link)", path)
        #     return True

        if path.endswith("/node_modules"):
            return False

        if not self.path_is_readable(path):
            if os.path.islink(path):
                log.warning("{}: path cannot be read [BROKEN LINK?]", path)
            else:
                log.warning("{}: path cannot be read", path)
            return False

        if not self.path_is_writable(path):
            log.warning("{}: path cannot be written", path)
            return False
        try:
            owner = system.get_username(os.stat(path).st_uid)
        except KeyError:
            owner = os.stat(path).st_uid

        if owner != self.current_os_user:
            if owner == 990:
                log.debug("{}: wrong owner ({})", path, owner)
            else:
                log.warning("{}: wrong owner ({})", path, owner)
            return False
        return True

    def inspect_permissions(self, root='.'):

        for root, sub_folders, files in os.walk(root):

            counter = 0
            for folder in sub_folders:
                if folder == '.git':
                    continue
                # produced by virtual-env?
                if folder == 'lib':
                    continue
                if folder.endswith("__pycache__"):
                    continue
                if folder.endswith(".egg-info"):
                    continue

                path = os.path.join(root, folder)
                if self.check_permissions(path):
                    self.inspect_permissions(root=path)

                counter += 1
                if counter > 20:
                    log.warning("Too many folders, stopped checks in {}", root)
                    break

            counter = 0
            for file in files:
                if file.endswith(".pyc"):
                    continue

                path = os.path.join(root, file)
                self.check_permissions(path)

                counter += 1
                if counter > 100:
                    log.warning("Too many files, stopped checks in {}", root)
                    break

            break

    def read_specs(self):
        """ Read project configuration """

        try:
            if self.initialize:
                read_extended = False
            elif self.install:
                read_extended = False
            else:
                read_extended = True

            confs = configuration.read_configuration(
                default_file_path=CONFS_DIR,
                base_project_path=self.ABS_PROJECT_PATH,
                projects_path=PROJECT_DIR,
                submodules_path=SUBMODULES_DIR,
                read_extended=read_extended,
                production=self.production
            )
            self.specs = confs[0]
            self.extended_project = confs[1]
            self.extended_project_path = confs[2]

            self.specs = configuration.mix_configuration(
                self.specs,
                self.arguments.host_configuration

            )

        except AttributeError as e:

            log.exit(e)

        self.vars = self.specs.get('variables', {})

        log.verbose("Configuration loaded")

        framework = glom(self.vars, "env.FRONTEND_FRAMEWORK", default=NO_FRONTEND)

        if framework == NO_FRONTEND:
            framework = None

        self.frontend = framework

        if self.frontend is not None:
            log.verbose("Frontend framework: {}", self.frontend)

        self.project_title = glom(self.specs, "project.title", default='Unknown title')
        self.version = glom(self.specs, "project.version", default=None)
        self.rapydo_version = glom(self.specs, "project.rapydo", default=None)
        self.project_description = glom(
            self.specs, "project.description", default='Unknown description'
        )

        if self.rapydo_version is None:
            log.exit("RAPyDo version not found in your project_configuration file")

    def preliminary_version_check(self):

        specs = configuration.load_yaml_file(
            file=configuration.PROJECT_CONF_FILENAME,
            path=self.ABS_PROJECT_PATH,
            keep_order=True
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

        if rapydo_version is None:
            return True

        r = LooseVersion(rapydo_version)
        c = LooseVersion(__version__)
        if r == c:
            return True

        if r > c:
            action = "Upgrade your controller to version {}".format(r)
        else:
            action = "Downgrade your controller to version {}".format(r)
            action += " or upgrade your project"

        msg = "RAPyDo version is not compatible"
        msg += "\n\nThis project requires rapydo {}, you are using {}\n\n{}\n".format(
            r, c, action)

        log.exit(msg)

    def check_internet_connection(self):
        """ Check if connected to internet """

        try:
            requests.get('https://www.google.com')
        except requests.ConnectionError:
            log.exit('Internet connection is unavailable')
        else:
            self.checked("Internet connection is available")
            self.tested_connection = True

    @staticmethod
    def check_time():
        # get online utc time
        http = urllib3.PoolManager()
        response = http.request('GET', "http://just-the-time.appspot.com/")

        internet_time = response.data.decode('utf-8')
        online_time = datetime.strptime(internet_time.strip(), "%Y-%m-%d %H:%M:%S")

        sec_diff = (datetime.utcnow() - online_time).total_seconds()

        major_diff = abs(sec_diff) >= 300
        minor_diff = abs(sec_diff) >= 60 if not major_diff else False

        if major_diff:
            log.error("Date misconfiguration on the host.")
        elif minor_diff:
            log.warning("Date misconfiguration on the host.")

        if major_diff or minor_diff:
            current_date = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
            tz_offset = time.timezone / -3600
            log.info("Current date: {} UTC", current_date)
            log.info("Expected: {} UTC", online_time)
            log.info("Current timezone: {} (offset = {}h)", time.tzname, tz_offset)

        if major_diff:
            tips = "To manually set the date: sudo date --set \"{}\"".format(
                online_time.strftime('%d %b %Y %H:%M:%S')
            )
            log.exit("Unable to continue, please fix the host date\n{}", tips)

    def working_clone(self, name, repo, from_path=None):

        # substitute values starting with '$$'
        myvars = {
            ANGULAR: self.frontend == ANGULAR,
            REACT: self.frontend == REACT
        }
        repo = services.apply_variables(repo, myvars)

        # Is this single repo enabled?
        repo_enabled = repo.pop('if', False)
        if not repo_enabled:
            return None

        repo['do'] = self.initialize
        repo['check'] = not self.install
        repo.setdefault('path', name)
        repo.setdefault(
            'branch',
            self.rapydo_version if self.rapydo_version else __version__
        )

        if from_path is not None:

            local_path = os.path.join(from_path, name)
            if not os.path.exists(local_path):
                log.exit("Submodule {} not found in {}", repo['path'], from_path)

            submodule_path = os.path.join(
                os.curdir, SUBMODULES_DIR, repo['path']
            )

            if os.path.exists(submodule_path):
                log.warning("Path {} already exists, removing", submodule_path)
                if os.path.isfile(submodule_path):
                    os.remove(submodule_path)
                elif os.path.islink(submodule_path):
                    os.remove(submodule_path)
                else:
                    shutil.rmtree(submodule_path)

            os.symlink(local_path, submodule_path)

        return gitter.clone(**repo)

    def git_submodules(self):
        """ Check and/or clone git projects """

        from_local_path = self.current_args.get('submodules_path')
        if from_local_path is not None:
            if not os.path.exists(from_local_path):
                log.exit("Local path not found: {}", from_local_path)

        repos = self.vars.get('submodules', {}).copy()

        self.gits['main'] = gitter.get_repo(".")

        for name, repo in repos.items():
            self.gits[name] = self.working_clone(name, repo, from_path=from_local_path)

    def read_composers(self):

        # Find configuration that tells us which files have to be read

        # substitute values starting with '$$'

        load_commons = not self.current_args.get('no_commons')
        load_frontend = not self.current_args.get('no_frontend')

        stack = self.current_args.get('stack')

        if stack is None:
            stack = "production" if self.production else "development"

        myvars = {
            'backend': not self.current_args.get('no_backend'),
            ANGULAR: self.frontend == ANGULAR and load_frontend,
            REACT: self.frontend == REACT and load_frontend,
            'commons': load_commons,
            'extended-commons': self.extended_project is not None and load_commons,
            'mode': "{}.yml".format(stack),
            'extended-mode': self.extended_project is not None,
            'baseconf': CONFS_DIR,
            'customconf': os.path.join(self.ABS_PROJECT_PATH, CONTAINERS_YAML_DIRNAME),
        }

        if self.extended_project_path is None:
            myvars['extendedproject'] = None
        else:
            myvars['extendedproject'] = os.path.join(
                self.extended_project_path, CONTAINERS_YAML_DIRNAME
            )

        compose_files = OrderedDict()

        confs = self.vars.get('composers', {})
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

    def get_services(self, default):

        value = self.current_args.get('services')

        if value is None:
            return default

        return value.split(',')

    def create_projectrc(self):
        templating = Templating()
        t = templating.get_template(
            'projectrc',
            {
                'project': self.project,
                'hostname': self.hostname,
                'production': self.production,
                'testing': TESTING,
                'services': self.active_services,
            }
        )
        templating.save_template(PROJECTRC, t, force=True)

        self.arguments.projectrc = configuration.load_yaml_file(
            PROJECTRC, path=os.curdir, is_optional=True
        )
        self.arguments.host_configuration = self.arguments.projectrc.pop(
            'project_configuration', {}
        )
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

        env = self.vars.get('env', {})
        env['PROJECT_DOMAIN'] = self.hostname
        env['COMPOSE_PROJECT_NAME'] = self.project
        env['VANILLA_DIR'] = os.path.abspath(os.curdir)
        env['SUBMODULE_DIR'] = os.path.join(env['VANILLA_DIR'], SUBMODULES_DIR)
        env['PROJECT_DIR'] = os.path.join(env['VANILLA_DIR'], PROJECT_DIR, self.project)

        if self.extended_project_path is None:
            env['EXTENDED_PROJECT_PATH'] = env['PROJECT_DIR']
        else:
            env['EXTENDED_PROJECT_PATH'] = os.path.join(
                env['VANILLA_DIR'], self.extended_project_path
            )

        if self.extended_project is None:
            env['EXTENDED_PROJECT'] = EXTENDED_PROJECT_DISABLED
        else:
            env['EXTENDED_PROJECT'] = self.extended_project

        env['RAPYDO_VERSION'] = __version__
        env['PROJECT_VERSION'] = self.version
        env['CURRENT_UID'] = self.current_uid
        env['CURRENT_GID'] = self.current_gid
        env['PROJECT_TITLE'] = self.project_title
        env['PROJECT_DESCRIPTION'] = self.project_description
        privileged_mode = self.current_args.get('privileged')
        env['DOCKER_PRIVILEGED_MODE'] = "true" if privileged_mode else "false"

        if self.action == "formatter" and self.current_args.get('folder') is not None:
            VANILLA_SUBMODULE = 'vanilla'
            submodule = self.current_args.get('submodule', VANILLA_SUBMODULE)

            if submodule == VANILLA_SUBMODULE:
                env['BLACK_SUBMODULE'] = ""
                env['BLACK_FOLDER'] = self.current_args.get('folder')
            else:
                env['BLACK_SUBMODULE'] = submodule
                env['BLACK_FOLDER'] = self.current_args.get('folder')

        if env.get('ACTIVATE_CELERYBEAT', "0") == "0":
            env['CELERYBEAT_SCHEDULER'] = 'Unknown'
        else:
            celery_backend = env.get('CELERY_BACKEND')
            if celery_backend is None:
                env['CELERYBEAT_SCHEDULER'] = 'Unknown'
            elif celery_backend == 'MONGODB':
                env['CELERYBEAT_SCHEDULER'] = 'celerybeatmongo.schedulers.MongoScheduler'
            elif celery_backend == 'REDIS':
                env['CELERYBEAT_SCHEDULER'] = 'redbeat.RedBeatScheduler'
            else:
                env['CELERYBEAT_SCHEDULER'] = 'Unknown'

        env['DOCKER_NETWORK_MODE'] = self.current_args.get('net', 'bridge')

        invalid_rabbit_characters = ['£', '§', '”', '’']
        pwd = env.get("RABBITMQ_PASSWORD")
        if any([c in pwd for c in invalid_rabbit_characters]):
            log.exit("""Invalid characters in RABBITMQ_PASSWORD.
Some special characters, including {}, should be avoided due to unexpected crashes
occurred during RabbitMQ startup """, ' '.join(invalid_rabbit_characters))

        with open(envfile, 'w+') as whandle:
            for key, value in sorted(env.items()):
                if value is None:
                    value = ''
                else:
                    value = str(value)
                if ' ' in value:
                    value = "'{}'".format(value)
                whandle.write("{}={}\n".format(key, value))
            log.verbose("Created {} file", COMPOSE_ENVIRONMENT_FILE)

    def check_placeholders(self):

        if len(self.active_services) == 0:
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

            for key, value in service.get('environment', {}).items():
                if PLACEHOLDER in str(value):
                    key = services.normalize_placeholder_variable(key)
                    missing.add(key)

        placeholders = []
        for key in missing:

            serv = services.vars_to_services_mapping.get(key)
            if serv is None:
                log.exit(
                    "Missing variable: {}. Cannot find a service mapping this variable",
                    key
                )

            active_serv = []
            for i in serv:
                if i in self.active_services:
                    active_serv.append(i)
            if len(active_serv) > 0:
                placeholders.append(
                    "{:<20}\trequired by\t{}".format(key, ', '.join(active_serv))
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

    def get_ignore_submodules(self):
        ignore_submodule = self.current_args.get('ignore_submodule', '')
        if ignore_submodule is None:
            return ''
        return ignore_submodule.split(",")

    def git_checks_or_update(self):

        ignore_submodule_list = self.get_ignore_submodules()

        for name, gitobj in self.gits.items():
            if name in ignore_submodule_list:
                log.debug("Skipping {} on {}", self.action, name)
                continue
            if gitobj is None:
                continue
            if self.update:
                gitter.update(name, gitobj)
            elif self.check:
                gitter.check_updates(name, gitobj)
                gitter.check_unstaged(name, gitobj)

    def get_bin_version(exec_cmd, option='--version'):

        output = None
        try:
            output = system.execute_command(exec_cmd, option)

            # try splitting on comma and/or parenthesis
            # then last element on spaces
            output = output.split('(')[0].split(',')[0].split()[::-1][0]
            output = output.strip()
            output = output.replace("'", "")

            return output
        except ProcessExecutionError as e:
            log.error("{} not found: {}", exec_cmd, e)
            return None
        except BaseException:
            log.critical("Cannot parse command output: {}", output)
            return output
