import os
import shutil
import signal
import sys
import tempfile

from git import Repo

from controller import __version__, gitter
from controller.app import Application
from controller.arguments import ArgParser
from controller.dockerizing import Dock
from controller.templating import Templating


class TemporaryRemovePath:
    def __init__(self, path):
        self.path = os.path.abspath(path)
        self.tmp_path = "{}.bak".format(self.path)

    def __enter__(self):

        os.rename(self.path, self.tmp_path)
        return self

    def __exit__(self, _type, value, tb):
        os.rename(self.tmp_path, self.path)


class Timeout(Exception):
    pass


def handler(signum, frame):
    raise Timeout("Time is up")


def mock_KeyboardInterrupt(signum, frame):
    raise KeyboardInterrupt("Time is up")


def exec_command(capfd, command, *asserts):

    with capfd.disabled():
        print("\n")
        print("_____________________________________________")
        print(command)
        print("_____________________________________________")

    try:
        arguments = ArgParser(args=command.split(" "))
        Application(arguments)
    # NOTE: docker-compose calls SystemExit at the end of the command...
    except SystemExit:
        pass

    captured = capfd.readouterr()
    # Remove empty lines
    out = [x for x in captured.out.replace("\r", "").split("\n") if x.strip()]
    err = [x for x in captured.err.replace("\r", "").split("\n") if x.strip()]

    with capfd.disabled():
        for o in out:
            print("_ {}".format(o))
        for e in err:
            print("! {}".format(e))

    for a in asserts:
        # Check if the assert is in any line (also as substring) from out or err
        assert a in out + err or any(a in x for x in out + err)

    return out


def test_failed_create(capfd):

    exec_command(
        capfd,
        "rapydo create first",
        "Missing authentication service, add --auth option",
    )

    with open("data/logs/rapydo-controller.log") as f:
        logs = f.read().splitlines()
        assert logs[-1].endswith("Missing authentication service, add --auth option")

    exec_command(
        capfd, "rapydo create first --auth xyz", "Invalid authentication service: xyz",
    )

    exec_command(
        capfd,
        "rapydo create first --auth postgres",
        "Missing frontend framework, add --frontend option",
    )

    exec_command(
        capfd,
        "rapydo create first --auth postgres --frontend xyz",
        "Invalid frontend framework: xyz",
    )

    exec_command(
        capfd,
        "rapydo create first --auth postgres --frontend angular",
        "Current folder is not empty, cannot create a new project here.",
        "Found: ",
        "Use --current to force the creation here",
    )

    # Please note that --current is required because data folder is already created
    # to be able to tests logs

    exec_command(
        capfd,
        "rapydo create test_celery --auth postgres --frontend angular --current ",
        "Wrong project name, _ is not a valid character",
    )

    exec_command(
        capfd,
        "rapydo create first --auth postgres --frontend angular --no-auto --current ",
        "mkdir -p projects",
    )

    exec_command(
        capfd,
        "rapydo create first --auth postgres --frontend no --env X --current ",
        "Invalid envs format, expected: K1=V1,K2=V2,...",
    )
    exec_command(
        capfd,
        "rapydo create first --auth postgres --frontend no --env X, --current ",
        "Invalid envs format, expected: K1=V1,K2=V2,...",
    )
    exec_command(
        capfd,
        "rapydo create first --auth postgres --frontend no --env X=1,Y --current ",
        "Invalid envs format, expected: K1=V1,K2=V2,...",
    )

    templating = Templating()
    with TemporaryRemovePath(templating.template_dir):
        exec_command(
            capfd,
            "rapydo create firsts --auth postgres --frontend no --current",
            "Template folder not found",
        )

    exec_command(
        capfd,
        "rapydo create celery --auth postgres --frontend angular --current ",
        "You selected a reserved name, invalid project name: celery",
    )


def test_create(capfd):
    # Let's create a project and init git
    create_command = "rapydo create first --auth postgres --frontend angular"
    create_command += " --services rabbit --add-optionals --current"
    create_command += " --origin https://your_remote_git/your_project.git"
    exec_command(
        capfd, create_command, "Project first successfully created",
    )

    pconf = "projects/first/project_configuration.yaml"
    os.remove(pconf)
    exec_command(
        capfd,
        "rapydo create first --auth postgres --frontend angular --current --no-auto",
        "Project folder already exists: projects/first/confs",
        "{f}".format(f=pconf),
    )

    create_command = "rapydo create first --auth postgres --frontend angular"
    create_command += " --services rabbit --env RABBITMQ_PASSWORD=invalid£password"
    create_command += " --current --force"
    exec_command(
        capfd,
        create_command,
        "Project folder already exists: projects/first/confs",
        "Project first successfully created",
    )

    create_command = "rapydo create first --auth postgres --frontend angular"
    create_command += " --services rabbit"
    create_command += " --current --force"
    exec_command(
        capfd,
        create_command,
        "Project folder already exists: projects/first/confs",
        "Project first successfully created",
    )

    # this is the last version that is created
    create_command = "rapydo create first --auth postgres --frontend angular"
    create_command += " --services rabbit"
    create_command += " --current --force"
    create_command += " --env CUSTOMVAR1=mycustomvalue,CUSTOMVAR2=mycustomvalue"
    exec_command(
        capfd,
        create_command,
        "Project folder already exists: projects/first/confs",
        "A backup of {f} is saved as {f}.bak".format(f=pconf),
        "Project first successfully created",
    )

    exec_command(
        capfd,
        "rapydo create first --auth postgres --frontend angular --current",
        "Project folder already exists: projects/first/confs",
        "Project file already exists: {}".format(pconf),
        "Project first successfully created",
    )

    exec_command(
        capfd,
        "rapydo create first --auth postgres --frontend angular --no-auto --current",
        "Project folder already exists: projects/first/confs",
        "Project file already exists: {}".format(pconf),
        "Project first successfully created",
    )

    # here a single and valid project is created (not initialized)


def test_all(capfd):

    exec_command(capfd, "rapydo", "usage")

    exec_command(
        capfd,
        "rapydo --invalid_option",
        'Wrong "--invalid_option" option provided.',
        "Arguments containing '_' are not allowed. Use '-' instead",
    )

    exec_command(
        capfd,
        "rapydo --invalid-option create first",
        "Unknown argument: --invalid-option",
        "Use --help to list options",
    )

    # This is to test a BUG fix: trailing space was interpreted as
    # additional empty commands raising an Unknown argument error.
    exec_command(
        capfd, "rapydo version ", "required rapydo",  # please note the trailing space
    )

    # Basic initialization
    exec_command(
        capfd,
        "rapydo check -i main",
        "Repo https://github.com/rapydo/http-api.git missing as ./submodules/http-api.",
        "You should init your project",
    )
    exec_command(
        capfd, "rapydo init", "Project initialized",
    )

    # Manipulate .projectrc to inject invalid options
    shutil.copy(".projectrc", ".projectrc.bak")

    with open(".projectrc", "a") as f:
        f.write("\ninvalid-opt: invalid\n")

    exec_command(
        capfd, "rapydo check", "Unknown parameter invalid-opt found in .projectrc"
    )
    shutil.copy(".projectrc.bak", ".projectrc")

    with open(".projectrc", "a") as f:
        f.write("\ninvalid:\n")
        f.write("  invalid-command: invalid\n")
    exec_command(capfd, "rapydo check", "Unknown command invalid found in .projectrc")
    shutil.copy(".projectrc.bak", ".projectrc")

    with open(".projectrc", "a") as f:
        f.write("\ncheck:\n")
        f.write("  invalid-opt: invalid\n")
    exec_command(
        capfd, "rapydo check", "Unknown parameter check/invalid-opt found in .projectrc"
    )
    shutil.copy(".projectrc.bak", ".projectrc")

    with open(".projectrc", "a") as f:
        f.write("\ncheck:\n")
        f.write("  ignore-submodule: main\n")
        f.write("  no-git: True\n")
        f.write("  no-builds: True\n")
    exec_command(
        capfd,
        "rapydo check",
        "Skipping git checks",
        "Skipping builds checks",
        "Checks completed",
    )
    shutil.copy(".projectrc.bak", ".projectrc")

    r = gitter.get_repo("submodules/http-api")
    gitter.switch_branch(r, "0.7.3")
    exec_command(
        capfd,
        "rapydo check -i main",
        "http-api: wrong branch 0.7.3, expected {}".format(__version__),
        "You can use rapydo init to fix it",
    )
    exec_command(
        capfd,
        "rapydo init",
        "Switched branch to origin/{} on http-api".format(__version__),
        "build-templates already set on branch {}".format(__version__),
        "do already set on branch {}".format(__version__),
    )

    with TemporaryRemovePath("data"):
        exec_command(
            capfd,
            "rapydo check -i main --no-git --no-builds",
            "Folder not found: data",
            "Please note that this command only works from inside a rapydo-like repo",
            "Verify that you are in the right folder, now you are in: ",
        )

    with TemporaryRemovePath("projects/first/builds"):
        exec_command(
            capfd,
            "rapydo check -i main --no-git --no-builds",
            "Project first is invalid: required folder not found projects/first/builds",
        )

    with TemporaryRemovePath(".gitignore"):
        exec_command(
            capfd,
            "rapydo check -i main --no-git --no-builds",
            "Project first is invalid: required file not found .gitignore",
        )

    # Do not test this with python 3.5
    if sys.version_info >= (3, 6):

        path = "projects/first/backend/apis/xyz.py"
        assert not os.path.exists(path)
        exec_command(
            capfd, "rapydo add endpoint xyz", "Endpoint created: {}".format(path),
        )
        exec_command(
            capfd, "rapydo add endpoint xyz", "{} already exists".format(path),
        )
        assert os.path.isfile(path)

        path = "projects/first/backend/tasks/xyz.py"
        assert not os.path.exists(path)
        exec_command(
            capfd, "rapydo add task xyz", "Task created: {}".format(path),
        )
        exec_command(
            capfd, "rapydo add task xyz", "{} already exists".format(path),
        )
        assert os.path.isfile(path)

        path = "projects/first/frontend/app/components/xyz"
        assert not os.path.exists(path)
        assert not os.path.exists(os.path.join(path, "xyz.ts"))
        assert not os.path.exists(os.path.join(path, "xyz.html"))
        exec_command(
            capfd,
            "rapydo add component xyz",
            "Added import { XyzComponent } from '@app/components/xyz/xyz'; to module ",
            "Added XyzComponent to module declarations",
            "Component created: {}".format(path),
        )
        assert os.path.isdir(path)
        assert os.path.isfile(os.path.join(path, "xyz.ts"))
        assert os.path.isfile(os.path.join(path, "xyz.html"))
        exec_command(
            capfd, "rapydo add component xyz", "{}/xyz.ts already exists".format(path),
        )
        shutil.rmtree(path)
        exec_command(
            capfd,
            "rapydo add component xyz",
            "Import already included in module file",
            "Added XyzComponent to module declarations",
            "Component created: {}".format(path),
        )

        path = "projects/first/frontend/app/services"
        assert not os.path.exists(path)
        assert not os.path.exists(os.path.join(path, "xyz.ts"))
        exec_command(
            capfd,
            "rapydo add service xyz",
            "Added import { XyzService } from '@app/services/xyz'; to module file",
            "Added XyzService to module declarations",
            "Service created: {}".format(path),
        )
        assert os.path.isdir(path)
        assert os.path.isfile(os.path.join(path, "xyz.ts"))
        exec_command(
            capfd, "rapydo add service xyz", "{}/xyz.ts already exists".format(path),
        )
        os.remove("{}/xyz.ts".format(path))
        exec_command(
            capfd,
            "rapydo add service xyz",
            "Import already included in module file",
            "Added XyzService to module declarations",
            "Service created: {}".format(path),
        )

        exec_command(
            capfd,
            "rapydo add abc xyz",
            "Invalid type abc, please chose one of:",
            "endpoint",
            "task",
            "component",
            "service",
        )

    # Basic pull
    exec_command(
        capfd, "rapydo -s xxx pull", "Invalid service name: xxx",
    )
    exec_command(
        capfd, "rapydo pull", "Base images pulled from docker hub",
    )

    # Skipping main because we are on a fake git repository
    exec_command(
        capfd, "rapydo update -i main", "All updated",
    )

    open("submodules/do/temp.file", "a").close()
    with open("submodules/do/setup.py", "a") as f:
        f.write("# added from tests\n")

    exec_command(
        capfd,
        "rapydo update -i main",
        "Unable to update do repo, you have unstaged files",
        "Untracked files:",
        "submodules/do/temp.file",
        "Changes not staged for commit:",
        "submodules/do/setup.py",
    )
    os.remove("submodules/do/temp.file")
    r = gitter.get_repo("submodules/do")
    r.git().execute(["git", "checkout", "--", "setup.py"])

    # Skipping main because we are on a fake git repository
    exec_command(
        capfd, "rapydo check -i main", "Checks completed",
    )

    os.rename("submodules", "submodules.bak")
    os.mkdir("submodules")

    # This is to re-fill the submodules folder,
    # these folder will be removed by the next init
    exec_command(capfd, "rapydo init", "Project initialized")

    modules_path = os.path.abspath("submodules.bak")

    with TemporaryRemovePath("submodules.bak/do"):
        exec_command(
            capfd,
            "rapydo init --submodules-path {}".format(modules_path),
            "Submodule do not found in ",
        )
    exec_command(
        capfd,
        "rapydo init --submodules-path {}".format(modules_path),
        "Path ./submodules/http-api already exists, removing",
        "Project initialized",
    )

    assert os.path.islink("submodules/do")
    assert not os.path.islink("submodules.bak/do")

    # Init again, this time in submodules there are links...
    # and will be removed as well as the folders
    exec_command(
        capfd,
        "rapydo init --submodules-path {}".format(modules_path),
        "Path ./submodules/http-api already exists, removing",
        "Project initialized",
    )

    exec_command(
        capfd,
        "rapydo init --submodules-path invalid/path",
        "Local path not found: invalid/path",
    )

    os.mkdir("submodules/rapydo-confs")
    exec_command(
        capfd,
        "rapydo check -i main --no-git --no-builds",
        "Project first contains an obsolete file or folder: submodules/rapydo-confs",
    )
    shutil.rmtree("submodules/rapydo-confs")
    # Some tests with list
    exec_command(
        capfd,
        "rapydo list",
        "Nothing to list, please use rapydo list -h for available options",
    )
    exec_command(
        capfd,
        "rapydo list --env",
        "List env variables:",
        "ACTIVATE_ALCHEMY",
        "CUSTOMVAR1",
        "CUSTOMVAR2",
        "mycustomvalue",
    )
    exec_command(
        capfd, "rapydo list --args", "List of configured rapydo arguments:",
    )
    exec_command(
        capfd, "rapydo list --submodules", "List of submodules:",
    )

    exec_command(
        capfd,
        "rapydo list --active-services",
        "List of active services:",
        "backend",
        "frontend",
        "postgres",
        "rabbit",
    )

    exec_command(
        capfd,
        "rapydo interfaces XYZ",
        "Container 'XYZui' is not defined",
        "You can use rapydo interfaces list to get available interfaces",
    )
    exec_command(
        capfd,
        "rapydo interfaces list",
        "List of available interfaces:",
        " - mongo",
        " - sqlalchemy",
        " - swagger",
        " - celery",
    )

    exec_command(
        capfd,
        "rapydo interfaces sqlalchemy --port XYZ --detach",
        "Port must be a valid integer",
    )

    exec_command(
        capfd,
        "rapydo interfaces sqlalchemy --detach",
        "Launching interface: sqlalchemyui",
        "docker-compose command: 'run'",
    )
    exec_command(
        capfd,
        "rapydo interfaces sqlalchemy --port 123 --detach",
        "Launching interface: sqlalchemyui",
        "docker-compose command: 'run'",
    )

    exec_command(
        capfd,
        "rapydo interfaces swagger --port 124 --detach",
        "You can access swaggerui web page here:",
        "http://localhost:124?docExpansion=list&",
        "url=http://localhost:8080/api/specs",
    )

    exec_command(
        capfd,
        "rapydo version",
        "rapydo: \033[1;32m{v}".format(v=__version__),
        "required rapydo: \033[1;32m{v}".format(v=__version__),
    )

    # docker dump
    exec_command(
        capfd, "rapydo dump", "Config dump: docker-compose.yml",
    )

    exec_command(capfd, "rapydo upgrade")
    exec_command(
        capfd, "rapydo upgrade --path invalid", "Invalid path, cannot upgrade invalid"
    )
    exec_command(capfd, "rapydo upgrade --path .gitignore")

    # Test selection with two projects
    exec_command(
        capfd,
        "rapydo create justanother --auth postgres --frontend no --current",
        "Project justanother successfully created",
    )

    os.remove(".projectrc")

    exec_command(
        capfd,
        "rapydo check -i main --no-git --no-builds",
        "Multiple projects found, please use --project to specify one of the following",
    )

    # Test with zero projects
    with TemporaryRemovePath("projects"):
        os.mkdir("projects")
        exec_command(
            capfd,
            "rapydo check -i main --no-git --no-builds",
            "No project found (projects folder is empty?)",
        )
        shutil.rmtree("projects")

    exec_command(
        capfd, "rapydo -p first check -i main --no-git --no-builds", "Checks completed",
    )

    # Check invalid and reserved project names
    exec_command(
        capfd,
        "rapydo -p invalid_character check -i main --no-git --no-builds",
        "Wrong project name, _ is not a valid character.",
    )
    exec_command(
        capfd,
        "rapydo -p celery check -i main --no-git --no-builds",
        "You selected a reserved name, invalid project name: celery",
    )
    exec_command(
        capfd,
        "rapydo -p fourth check -i main --no-git --no-builds",
        "Wrong project fourth",
        "Select one of the following: ",
    )

    # Test init of data folders
    shutil.rmtree("data/logs")
    assert not os.path.isdir("data/logs")
    # Let's restore .projectrc and data/logs
    exec_command(
        capfd, "rapydo --project first init", "Project initialized",
    )
    assert os.path.isdir("data/logs")
    exec_command(
        capfd, "rapydo check -i main --no-git --no-builds", "Checks completed",
    )

    # Test dirty repo
    fin = open("submodules/do/new_file", "wt+")
    fin.write("xyz")
    fin.close()

    fin = open("submodules/build-templates/backend/Dockerfile", "a")
    fin.write("xyz")
    fin.close()
    r = Repo("submodules/build-templates")
    r.git.commit("-a", "-m", "'fake'")

    exec_command(
        capfd,
        "rapydo check -i main",
        "You have unstaged files on do",
        "Untracked files:",
        "submodules/do/new_file",
        "Obsolete image rapydo/backend:{}".format(__version__),
        "built on ",
        " but changed on ",
        "Update it with: rapydo --services backend pull",
    )

    exec_command(capfd, "rapydo verify sqlalchemy", "No container found for backend_1")

    exec_command(
        capfd, "rapydo -s invalid start", "No such service: invalid",
    )

    # Let's start with the stack
    exec_command(
        capfd, "rapydo start", "docker-compose command: 'up'", "Stack started",
    )

    exec_command(
        capfd,
        "rapydo status",
        "docker-compose command: 'ps'",
        # "first_backend_1",
    )

    exec_command(
        capfd, "rapydo shell backend --command hostname", "backend-server",
    )

    signal.signal(signal.SIGALRM, handler)
    signal.alarm(2)

    interrupted = False
    try:
        exec_command(
            capfd,
            "rapydo shell backend --default-command",
            "*** RESTful HTTP API ***",
            "Serving Flask app",
        )

    except Timeout:
        interrupted = True
    assert interrupted

    signal.signal(signal.SIGALRM, handler)
    signal.alarm(2)

    interrupted = False
    try:
        exec_command(
            capfd, "rapydo shell backend", "developer@backend-server:[/code]",
        )

    except Timeout:
        interrupted = True
    assert interrupted

    # Testing default users
    exec_command(
        capfd, "rapydo shell backend --command whoami", "developer",
    )
    exec_command(
        capfd, "rapydo shell frontend --command whoami", "node",
    )
    # No default user for rabbit container
    exec_command(
        capfd, "rapydo shell rabbit --command whoami", "root",
    )
    exec_command(
        capfd, "rapydo shell postgres --command whoami", "postgres",
    )

    exec_command(
        capfd,
        "rapydo scale rabbit",
        "Please specify how to scale: SERVICE=NUM_REPLICA",
        "You can also set a DEFAULT_SCALE_RABBIT variable in your .projectrc file",
    )
    exec_command(
        capfd, "rapydo scale rabbit=x", "Invalid number of replicas: x",
    )

    exec_command(
        capfd,
        "rapydo scale rabbit=2",
        "Starting first_rabbit_1",
        "Creating first_rabbit_2",
    )

    with open(".projectrc", "a") as f:
        f.write("\n      DEFAULT_SCALE_RABBIT: 3\n")

    exec_command(
        capfd,
        "rapydo scale rabbit",
        "Starting first_rabbit_1",
        "Starting first_rabbit_2",
        "Creating first_rabbit_3",
    )

    exec_command(
        capfd,
        "rapydo scale rabbit=1",
        "Starting first_rabbit_1",
        "Stopping and removing first_rabbit_2",
        "Stopping and removing first_rabbit_3",
    )

    exec_command(
        capfd,
        "rapydo logs -s backend --tail 10",
        "docker-compose command: 'logs'",
        "backend_1",
    )

    signal.signal(signal.SIGALRM, mock_KeyboardInterrupt)
    signal.alarm(3)
    try:
        exec_command(
            capfd,
            "rapydo logs -s backend --tail 10 --follow",
            "docker-compose command: 'logs'",
            "Stopped by keyboard",
        )
    except Exception as e:
        print(e)

    # Template project is based on sql
    exec_command(capfd, "rapydo verify neo4j", "Service neo4j not detected")
    exec_command(capfd, "rapydo verify sqlalchemy", "Service sqlalchemy is reachable")

    exec_command(
        capfd, "rapydo stop", "Stack stopped",
    )

    exec_command(
        capfd, "rapydo restart", "Stack restarted",
    )

    exec_command(
        capfd,
        "rapydo -s backend remove --net",
        "Incompatibile options --networks and --services",
    )

    exec_command(
        capfd,
        "rapydo -s backend remove --all",
        "Incompatibile options --all and --services",
    )

    exec_command(
        capfd, "rapydo remove", "docker-compose command: 'stop'", "Stack removed",
    )

    exec_command(
        capfd, "rapydo remove --networks", "Stack removed",
    )

    exec_command(
        capfd, "rapydo remove --all", "Stack removed",
    )

    exec_command(
        capfd,
        "rapydo shell backend --command hostname",
        "No container found for backend_1",
    )

    signal.signal(signal.SIGALRM, handler)
    signal.alarm(4)

    interrupted = False
    try:
        exec_command(
            capfd,
            "rapydo -s backend start --no-detach",
            "REST API backend server is ready to be launched",
        )
    except Timeout:
        interrupted = True
    assert interrupted

    # This is because after start --no-detach the container in still in exited status
    exec_command(
        capfd,
        "rapydo volatile backend --command hostname",
        "Bind for 0.0.0.0:8080 failed: port is already allocated",
    )

    exec_command(
        capfd, "rapydo remove --all", "Stack removed",
    )

    exec_command(
        capfd, "rapydo volatile backend --command hostname", "backend-server",
    )

    signal.signal(signal.SIGALRM, handler)
    signal.alarm(4)

    interrupted = False
    try:
        exec_command(
            capfd,
            "rapydo volatile maintenance",
            "Maintenance server is up and waiting for connections",
        )
    except Timeout:
        interrupted = True
    assert interrupted

    pconf = "projects/first/project_configuration.yaml"

    exec_command(
        capfd,
        "rapydo --prod check -i main --no-git --no-builds",
        "The following variables are missing in your configuration",
    )

    exec_command(
        capfd,
        "rapydo --prod init -f",
        "Created default .projectrc file",
        "Project initialized",
    )

    exec_command(
        capfd,
        "rapydo --prod interfaces swagger --port 124 --detach",
        "You can access swaggerui web page here:",
        "http://localhost:124?docExpansion=list&",
        "url=https://localhost/api/specs",
    )

    exec_command(
        capfd, "rapydo --prod -s proxy pull", "Base images pulled from docker hub",
    )

    exec_command(
        capfd, "rapydo ssl", "No container found for proxy_1",
    )
    exec_command(
        capfd, "rapydo ssl-certificate", "Deprecated command, use rapydo ssl instead",
    )
    exec_command(
        capfd,
        "rapydo ssl --volatile",
        "Creating a self signed SSL certificate",
        "Self signed SSL certificate successfully created",
        # Just to verify that the default does not change
        "Generating DH parameters, 1024 bit long safe prime, generator 2",
    )

    exec_command(
        capfd, "rapydo ssl --force", "No container found for proxy_1",
    )
    exec_command(
        capfd,
        "rapydo ssl --chain-file /file",
        "Invalid chain file (you provided /file)",
    )
    exec_command(
        capfd, "rapydo ssl --key-file /file", "Invalid chain file (you provided none)",
    )
    exec_command(
        capfd,
        "rapydo ssl --chain-file {f}".format(f=pconf),
        "Invalid key file (you provided none)",
    )
    exec_command(
        capfd,
        "rapydo ssl --chain-file {f} --key-file /file".format(f=pconf),
        "Invalid key file (you provided /file)",
    )
    exec_command(
        capfd,
        "rapydo ssl --chain-file {f} --key-file {f}".format(f=pconf),
        "Unable to automatically perform the requested operation",
        "You can execute the following commands by your-self:",
    )

    exec_command(
        capfd, "rapydo dhparam", "No container found for proxy_1",
    )

    ####################
    # ### TEST BUILD ###
    ####################

    create_command = "rapydo create testbuild --auth postgres --frontend angular"
    create_command += " --services rabbit --add-optionals --current"
    exec_command(
        capfd, create_command, "Project testbuild successfully created",
    )

    # Restore the default project
    exec_command(
        capfd, "rapydo -p testbuild init --force", "Project initialized",
    )

    # Add a custom image to extend base rabbit image:
    with open("projects/testbuild/confs/commons.yml", "a") as f:
        f.write(
            """
services:
  rabbit:
    build: ${PROJECT_DIR}/builds/rabbit
    image: ${COMPOSE_PROJECT_NAME}/rabbit:${RAPYDO_VERSION}

    """
        )

    os.makedirs("projects/testbuild/builds/rabbit")

    # Missing Dockerfile
    exec_command(
        capfd,
        "rapydo -s rabbit build",
        "No such file or directory: ",
        "projects/testbuild/builds/rabbit/Dockerfile",
    )

    # Empty Dockerfile
    with open("projects/testbuild/builds/rabbit/Dockerfile", "w+") as f:
        pass
    exec_command(
        capfd,
        "rapydo -s rabbit build",
        "Build failed, is ",
        "projects/testbuild/builds/rabbit/Dockerfile empty?",
    )

    # Missing base image
    with open("projects/testbuild/builds/rabbit/Dockerfile", "w+") as f:
        f.write("RUN ls")
    exec_command(
        capfd,
        "rapydo -s rabbit build",
        "No base image found ",
        "projects/testbuild/builds/rabbit/Dockerfile, unable to build",
    )

    # Not a RAPyDo child
    with open("projects/testbuild/builds/rabbit/Dockerfile", "w+") as f:
        f.write("FROM ubuntu")
    exec_command(
        capfd, "rapydo -s rabbit build", "No custom images to build",
    )

    # Invalid RAPyDo template
    with open("projects/testbuild/builds/rabbit/Dockerfile", "w+") as f:
        f.write("FROM rapydo/invalid")
    exec_command(
        capfd,
        "rapydo -s rabbit build",
        "Unable to find rapydo/invalid in this project",
        "Please inspect the FROM image in",
        "projects/testbuild/builds/rabbit/Dockerfile",
    )

    with open("projects/testbuild/builds/rabbit/Dockerfile", "w+") as f:
        f.write(
            """
FROM rapydo/rabbitmq:{}
# Just a simple command to differentiate from the parent
RUN mkdir xyz
""".format(
                __version__
            )
        )

    r = Repo(".")
    r.git.add("-A")
    r.git.commit("-a", "-m", "'fake'")

    # Selected a very fast service to speed up tests
    # Build custom rabbit image from pulled image
    exec_command(
        capfd,
        "rapydo -s rabbit build",
        "Successfully built",
        "Successfully tagged testbuild/rabbit:{}".format(__version__),
        "Custom images built",
    )

    exec_command(
        capfd, "rapydo ancestors XYZ", "No child found for XYZ",
    )

    dock = Dock()
    img = dock.images().pop(0)
    # sha256:c1a845de80526fcab136f9fab5f83BLABLABLABLABLA
    img_id = dock.image_info(img).get("Id")
    # => c1a845de8052
    img_id = img_id[7:19]
    exec_command(
        capfd,
        "rapydo ancestors {}".format(img_id),
        "Finding all children and (grand)+ children of {}".format(img_id),
    )

    # sha256:c1a845de80526fcab136f9fab5f83BLABLABLABLABLA
    img_id = dock.image_info("rapydo/rabbitmq:{}".format(__version__)).get("Id")
    # => c1a845de8052
    img_id = img_id[7:19]
    # rapydo/rabbitmq has a child: testbuild/rabbit just created
    exec_command(
        capfd,
        "rapydo ancestors {}".format(img_id),
        "Finding all children and (grand)+ children of {}".format(img_id),
        "testbuild/rabbit",
    )

    # Rebuild core rabbit image => custom rabbit is now obsolete
    # Please note the use of the first project.
    # This way we prevent to rebuilt the custom image of testbuild
    # This simulate a pull updating a core image making the custom image obsolete
    exec_command(
        capfd,
        "rapydo -p first -s rabbit build --core",
        "Core images built",
        "No custom images to build",
    )
    exec_command(
        capfd,
        "rapydo check -i main --no-git",
        "Obsolete image testbuild/rabbit:{}".format(__version__),
        "built on ",
        " that changed on ",
        "Update it with: rapydo --services rabbit build",
    )

    # rabbit images has no longer any child because it is just rebuilt
    exec_command(
        capfd,
        "rapydo ancestors {}".format(img_id),
        "Finding all children and (grand)+ children of {}".format(img_id),
    )

    # Add a second service with the same image to test redundant builds
    with open("projects/testbuild/confs/commons.yml", "a") as f:
        f.write(
            """
  rabbit2:
    build: ${PROJECT_DIR}/builds/rabbit
    image: ${COMPOSE_PROJECT_NAME}/rabbit:${RAPYDO_VERSION}

    """
        )

    exec_command(
        capfd,
        "rapydo -s rabbit,rabbit2 build",
        "Cannot determine build priority between rabbit and rabbit2",
        "Removed redundant services from ['rabbit', 'rabbit2'] -> ['rabbit2']",
    )

    # Restore the default project
    exec_command(
        capfd, "rapydo -p first init --force", "Project initialized",
    )


def test_extend(capfd):
    # base project is --auth postgres --frontend angular
    # the ext one is --auth neo4j --frontend angular
    exec_command(
        capfd,
        "rapydo create base --auth neo4j --frontend no --current",
        "Project folder already exists: projects",
        "Project base successfully created",
    )

    exec_command(
        capfd,
        "rapydo create new --extend new --auth neo4j --frontend no --current",
        "A project cannot extend itself",
    )
    exec_command(
        capfd,
        "rapydo create new --extend doesnotexist --auth neo4j --frontend no --current",
        "Invalid extend value: project doesnotexist not found",
    )

    create_command = "rapydo create ext --extend base"
    create_command += " --auth neo4j --frontend angular"
    create_command += " --current --services rabbit"
    exec_command(
        capfd,
        create_command,
        "Project folder already exists: projects",
        "Project ext successfully created",
    )

    exec_command(
        capfd, "rapydo -p ext init --force", "Project initialized",
    )
    exec_command(
        capfd, "rapydo -p ext check -i main --no-git --no-builds", "Checks completed",
    )


def test_services_activation(capfd):

    os.remove(".projectrc")

    # Test services activation from create --services
    services = [
        "postgres",
        "mysql",
        "neo4j",
        "mongo",
        "rabbit",
        "redis",
        "irods",
        "celery",
        "pushpin",
        "ftp",
    ]
    opt = "--frontend no --current --force"
    for service in services:

        if service == "postgres":
            auth = "postgres"
            serv_opt = ""
        elif service == "mysql":
            auth = "mysql"
            serv_opt = ""
        elif service == "neo4j":
            auth = "neo4j"
            serv_opt = ""
        elif service == "mongo":
            auth = "mongo"
            serv_opt = ""
        else:
            auth = "postgres"
            serv_opt = "--services {}".format(service)

        exec_command(
            capfd,
            "rapydo create testservices {opt} --auth {auth} {service}".format(
                opt=opt, auth=auth, service=serv_opt
            ),
            "Project testservices successfully created",
        )
        if service == "mysql":
            service = ["mariadb"]
        elif service == "irods":
            service = ["icat"]
        elif service == "celery":
            service = ["celery", "celeryui", "rabbit"]
        else:
            service = [service]

        exec_command(
            capfd,
            "rapydo -p testservices list --active-services",
            "List of active services:",
            *service,
        )


def test_rabbit_invalid_characters(capfd):

    create_command = "rapydo create testinvalid --auth postgres --frontend angular"
    create_command += " --services rabbit --env RABBITMQ_PASSWORD=invalid£password"
    create_command += " --current --force"
    exec_command(
        capfd, create_command, "Project testinvalid successfully created",
    )

    informative = "Some special characters, including £ § ” ’, are not allowed "
    informative = "because make RabbitMQ crash at startup"

    exec_command(
        capfd,
        "rapydo -p testinvalid init --force",
        "Not allowed characters found in RABBITMQ_PASSWORD.",
        informative,
    )

    shutil.rmtree("projects/testinvalid")

    # Restore the default project
    exec_command(
        capfd, "rapydo -p first init --force", "Project initialized",
    )


def test_install(capfd):

    exec_command(
        capfd,
        "rapydo install --pip --editable auto",
        "--pip and --editable options are not compatible",
    )

    exec_command(
        capfd,
        "rapydo install --user --editable auto",
        "--user and --editable options are not compatible",
    )

    with TemporaryRemovePath("submodules/do"):
        exec_command(
            capfd,
            "rapydo install --editable auto",
            "missing as ./submodules/do. You should init your project",
        )

    # I hope that one day this test will fail! :-)
    exec_command(capfd, "rapydo install --editable 1.0", "Invalid version")

    exec_command(
        capfd, "rapydo install --editable auto",
    )

    r = gitter.get_repo("submodules/do")
    gitter.switch_branch(r, "0.7.3")

    exec_command(
        capfd,
        "rapydo install --editable auto",
        "Controller repository switched to {}".format(__version__),
    )

    exec_command(
        capfd, "rapydo install --editable auto",
    )

    exec_command(
        capfd, "rapydo install --user auto",
    )

    # This is the very last command... installing an old version!
    exec_command(
        capfd, "rapydo install --pip --user 0.7.2",
    )

    # This test will change the required version
    pconf = "projects/first/project_configuration.yaml"

    # Read and change the content
    fin = open(pconf)
    data = fin.read()
    data = data.replace("rapydo: {}".format(__version__), "rapydo: 0.7.3")
    fin.close()
    # Write the new content
    fin = open(pconf, "wt")
    fin.write(data)
    fin.close()

    exec_command(
        capfd,
        "rapydo version",
        "This project is not compatible with rapydo version {}".format(__version__),
        "Please downgrade rapydo to version 0.7.3 or modify this project",
    )

    # Read and change the content
    fin = open(pconf)
    data = fin.read()
    data = data.replace("rapydo: 0.7.3", "rapydo: 99.99.99")
    fin.close()
    # Write the new content
    fin = open(pconf, "wt")
    fin.write(data)
    fin.close()

    exec_command(
        capfd,
        "rapydo version",
        "This project is not compatible with rapydo version {}".format(__version__),
        "Please upgrade rapydo to version 99.99.99 or modify this project",
    )


# Some final tests
def test_lastest(capfd):

    exec_command(
        capfd,
        "rapydo create latest --auth postgres --frontend no --current --force",
        "Project latest successfully created",
    )

    folder = os.getcwd()
    # Tests from a subfolder
    os.chdir("projects")
    exec_command(
        capfd,
        "rapydo -p latest check -i main --no-git --no-builds",
        "You are not in the main folder",
        "Checks completed",
    )

    # Tests from outside the folder
    os.chdir(tempfile.gettempdir())
    exec_command(
        capfd,
        "rapydo check -i main",
        "You are not in a git repository",
        "Please note that this command only works from inside a rapydo-like repository",
        "Verify that you are in the right folder, now you are in:",
    )

    os.chdir(folder)
