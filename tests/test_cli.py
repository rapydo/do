import os
import shutil
import signal
import tempfile
from collections import OrderedDict  # can be removed from python 3.7

from git import Repo
from typer.testing import CliRunner

from controller import __version__, gitter
from controller.app import Application
from controller.dockerizing import Dock
from controller.project import Project
from controller.templating import Templating

controller = Application()
runner = CliRunner()


class TemporaryRemovePath:
    def __init__(self, path):
        self.path = os.path.abspath(path)
        self.tmp_path = f"{self.path}.bak"

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


def exec_command(capfd, command, *asserts, input_text=None):

    with capfd.disabled():
        print("\n")
        print("_____________________________________________")
        print(f"rapydo {command}")

    # re-read everytime before invoking a command to cleanup the Configuration class
    Application.load_projectrc()
    Application.project_scaffold = Project()
    Application.gits = OrderedDict()
    result = runner.invoke(controller.app, command, input=input_text)

    with capfd.disabled():
        print(f"Exit code: {result.exit_code}")
        print(result.stdout)
        print("_____________________________________________")

    captured = capfd.readouterr()

    # Here outputs from inside the containers
    cout = [x for x in captured.out.replace("\r", "").split("\n") if x.strip()]
    # Here output from rapydo
    err = [x for x in captured.err.replace("\r", "").split("\n") if x.strip()]
    # Here output from other sources, e.g. typer errors o docker-compose output
    out = [x for x in result.stdout.replace("\r", "").split("\n") if x.strip()]
    # Here exceptions, e.g. Time is up
    if result.exception:
        exc = [
            x for x in str(result.exception).replace("\r", "").split("\n") if x.strip()
        ]
    else:
        exc = []

    with capfd.disabled():
        for e in err:
            print(f"{e}")
        for o in cout:
            print(f">> {o}")
        for o in out:
            print(f"_ {o}")
        if result.exception and str(result.exception) != result.exit_code:
            print("\n!! Exception:")
            print(result.exception)

    for a in asserts:
        # Check if the assert is in any line (also as substring) from out or err
        assert a in out + err or any(a in x for x in out + err + cout + exc)

    return out


def test_failed_create(capfd):

    exec_command(
        capfd, "--version", f"rapydo version: {__version__}",
    )
    exec_command(
        capfd, "create first", "Missing authentication service, add --auth option",
    )

    with open("data/logs/rapydo-controller.log") as f:
        logs = f.read().splitlines()
        assert logs[-1].endswith("Missing authentication service, add --auth option")

    exec_command(
        capfd, "create first --auth xyz", "Invalid authentication service: xyz",
    )

    exec_command(
        capfd,
        "create first --auth postgres",
        "Missing frontend framework, add --frontend option",
    )

    exec_command(
        capfd,
        "create first --auth postgres --frontend xyz",
        "Invalid frontend framework: xyz",
    )

    exec_command(
        capfd,
        "create first --auth postgres --frontend angular",
        "Current folder is not empty, cannot create a new project here.",
        "Found: ",
        "Use --current to force the creation here",
    )

    # Please note that --current is required because data folder is already created
    # to be able to tests logs

    exec_command(
        capfd,
        "create test_celery --auth postgres --frontend angular --current",
        "Wrong project name, _ is not a valid character",
    )

    exec_command(
        capfd,
        "create first --auth postgres --frontend angular --no-auto --current",
        "mkdir -p projects",
    )

    exec_command(
        capfd,
        "create first --auth postgres --frontend no --env X --current",
        "Invalid env X, expected: K1=V1",
    )
    exec_command(
        capfd,
        "create first --auth postgres --frontend no --env X, --current",
        "Invalid env X,, expected: K1=V1",
    )
    exec_command(
        capfd,
        "create first --auth postgres --frontend no --env X=a,Y=b --current",
        "Invalid env X=a,Y=b, expected: K1=V1",
    )

    templating = Templating()
    with TemporaryRemovePath(templating.template_dir):
        exec_command(
            capfd,
            "create firsts --auth postgres --frontend no --current",
            "Template folder not found",
        )

    exec_command(
        capfd,
        "create celery --auth postgres --frontend angular --current",
        "You selected a reserved name, invalid project name: celery",
    )


def test_create(capfd):
    # Let's create a project and init git
    create_command = "create first --auth postgres --frontend angular"
    create_command += " --service rabbit --service neo4j --add-optionals --current"
    create_command += " --origin-url https://your_remote_git/your_project.git"
    exec_command(
        capfd, create_command, "Project first successfully created",
    )

    pconf = "projects/first/project_configuration.yaml"
    os.remove(pconf)
    exec_command(
        capfd,
        "create first --auth postgres --frontend angular --current --no-auto",
        "Project folder already exists: projects/first/confs",
        f"{pconf}",
    )

    create_command = "create first --auth postgres --frontend angular"
    create_command += " --service rabbit --env RABBITMQ_PASSWORD=invalid£password"
    create_command += " --current --force"
    exec_command(
        capfd,
        create_command,
        "Project folder already exists: projects/first/confs",
        "Project first successfully created",
    )

    create_command = "create first --auth postgres --frontend angular"
    create_command += " --service rabbit --service neo4j"
    create_command += " --current --force"
    exec_command(
        capfd,
        create_command,
        "Project folder already exists: projects/first/confs",
        "Project first successfully created",
    )

    # this is the last version that is created
    create_command = "create first --auth postgres --frontend angular"
    create_command += " --service rabbit --service neo4j"
    create_command += " --current --force"
    create_command += " --env CUSTOMVAR1=mycustomvalue --env CUSTOMVAR2=mycustomvalue"
    exec_command(
        capfd,
        create_command,
        "Project folder already exists: projects/first/confs",
        "A backup of {f} is saved as {f}.bak".format(f=pconf),
        "Project first successfully created",
    )

    exec_command(
        capfd,
        "create first --auth postgres --frontend angular --current",
        "Project folder already exists: projects/first/confs",
        f"Project file already exists: {pconf}",
        "Project first successfully created",
    )

    exec_command(
        capfd,
        "create first --auth postgres --frontend angular --no-auto --current",
        "Project folder already exists: projects/first/confs",
        f"Project file already exists: {pconf}",
        "Project first successfully created",
    )

    # here a single and valid project is created (not initialized)


def test_all(capfd):

    exec_command(capfd, "rapydo", "Usage")

    exec_command(
        capfd,
        "--invalid-option create first",
        "Error: no such option: --invalid-option",
    )

    # Basic initialization
    exec_command(
        capfd,
        "check -i main",
        "Repo https://github.com/rapydo/http-api.git missing as submodules/http-api.",
        "You should init your project",
    )
    exec_command(
        capfd, "init", "Project initialized",
    )

    r = gitter.get_repo("submodules/http-api")
    gitter.switch_branch(r, "0.7.3")
    exec_command(
        capfd,
        "check -i main",
        f"http-api: wrong branch 0.7.3, expected {__version__}",
        "You can use rapydo init to fix it",
    )
    exec_command(
        capfd,
        "init",
        f"Switched branch to origin/{__version__} on http-api",
        f"build-templates already set on branch {__version__}",
        f"do already set on branch {__version__}",
    )

    with TemporaryRemovePath("data"):
        exec_command(
            capfd,
            "check -i main --no-git --no-builds",
            "Folder not found: data",
            "Please note that this command only works from inside a rapydo-like repo",
            "Verify that you are in the right folder, now you are in: ",
        )

    with TemporaryRemovePath("projects/first/builds"):
        exec_command(
            capfd,
            "check -i main --no-git --no-builds",
            "Project first is invalid: required folder not found projects/first/builds",
        )

    with TemporaryRemovePath(".gitignore"):
        exec_command(
            capfd,
            "check -i main --no-git --no-builds",
            "Project first is invalid: required file not found .gitignore",
        )

    path = "projects/first/backend/apis/xyz.py"
    assert not os.path.exists(path)
    exec_command(
        capfd, "add endpoint xyz", f"Endpoint created: {path}",
    )
    exec_command(
        capfd, "add endpoint xyz", f"{path} already exists",
    )
    assert os.path.isfile(path)

    path = "projects/first/backend/tasks/xyz.py"
    assert not os.path.exists(path)
    exec_command(
        capfd, "add task xyz", f"Task created: {path}",
    )
    exec_command(
        capfd, "add task xyz", f"{path} already exists",
    )
    assert os.path.isfile(path)

    path = "projects/first/frontend/app/components/xyz"
    assert not os.path.exists(path)
    assert not os.path.exists(os.path.join(path, "xyz.ts"))
    assert not os.path.exists(os.path.join(path, "xyz.html"))
    exec_command(
        capfd,
        "add component xyz",
        "Added import { XyzComponent } from '@app/components/xyz/xyz'; to module ",
        "Added XyzComponent to module declarations",
        f"Component created: {path}",
    )
    assert os.path.isdir(path)
    assert os.path.isfile(os.path.join(path, "xyz.ts"))
    assert os.path.isfile(os.path.join(path, "xyz.html"))
    exec_command(
        capfd, "add component xyz", f"{path}/xyz.ts already exists",
    )
    shutil.rmtree(path)
    exec_command(
        capfd,
        "add component xyz",
        "Import already included in module file",
        "Added XyzComponent to module declarations",
        f"Component created: {path}",
    )

    path = "projects/first/frontend/app/services"
    assert not os.path.exists(path)
    assert not os.path.exists(os.path.join(path, "xyz.ts"))
    exec_command(
        capfd,
        "add service xyz",
        "Added import { XyzService } from '@app/services/xyz'; to module file",
        "Added XyzService to module declarations",
        f"Service created: {path}",
    )
    assert os.path.isdir(path)
    assert os.path.isfile(os.path.join(path, "xyz.ts"))
    exec_command(
        capfd, "add service xyz", f"{path}/xyz.ts already exists",
    )
    os.remove(f"{path}/xyz.ts")
    exec_command(
        capfd,
        "add service xyz",
        "Import already included in module file",
        "Added XyzService to module declarations",
        f"Service created: {path}",
    )

    exec_command(
        capfd,
        "add abc xyz",
        "invalid choice: abc. (choose from endpoint, task, component, service)",
    )

    # Basic pull
    exec_command(
        capfd, "-s xxx pull", "Invalid service name: xxx",
    )
    exec_command(
        capfd, "pull", "Base images pulled from docker hub",
    )

    # Skipping main because we are on a fake git repository
    exec_command(
        capfd, "update -i main", "All updated",
    )

    open("submodules/do/temp.file", "a").close()
    with open("submodules/do/setup.py", "a") as f:
        f.write("# added from tests\n")

    exec_command(
        capfd,
        "update -i main",
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
        capfd, "check -i main", "Checks completed",
    )

    exec_command(
        capfd,
        "--stack invalid check -i main",
        "Failed to read projects/first/confs/invalid.yml: File does not exist",
    )

    os.rename("submodules", "submodules.bak")
    os.mkdir("submodules")

    # This is to re-fill the submodules folder,
    # these folder will be removed by the next init
    exec_command(capfd, "init", "Project initialized")

    modules_path = os.path.abspath("submodules.bak")

    with TemporaryRemovePath("submodules.bak/do"):
        exec_command(
            capfd,
            f"init --submodules-path {modules_path}",
            "Submodule do not found in ",
        )
    exec_command(
        capfd,
        f"init --submodules-path {modules_path}",
        "Path submodules/http-api already exists, removing",
        "Project initialized",
    )

    assert os.path.islink("submodules/do")
    assert not os.path.islink("submodules.bak/do")

    # Init again, this time in submodules there are links...
    # and will be removed as well as the folders
    exec_command(
        capfd,
        f"init --submodules-path {modules_path}",
        "Path submodules/http-api already exists, removing",
        "Project initialized",
    )

    exec_command(
        capfd,
        "init --submodules-path invalid/path",
        "Local path not found: invalid/path",
    )

    os.mkdir("submodules/rapydo-confs")
    exec_command(
        capfd,
        "check -i main --no-git --no-builds",
        "Project first contains an obsolete file or folder: submodules/rapydo-confs",
    )
    shutil.rmtree("submodules/rapydo-confs")
    # Some tests with list
    exec_command(
        capfd,
        "list",
        "Missing argument 'ELEMENT_TYPE:[env|services|submodules]'.  Choose from:",
    )
    exec_command(
        capfd,
        "list env",
        "List env variables:",
        "ACTIVATE_ALCHEMY",
        "CUSTOMVAR1",
        "CUSTOMVAR2",
        "mycustomvalue",
    )
    exec_command(
        capfd, "list submodules", "List of submodules:",
    )

    exec_command(
        capfd,
        "list services",
        "List of active services:",
        "backend",
        "frontend",
        "postgres",
        "rabbit",
    )

    exec_command(
        capfd,
        "list invalid",
        "Invalid value for 'ELEMENT_TYPE:[env|services|submodules]': ",
        "invalid choice: invalid. (choose from env, services, submodules)",
    )

    exec_command(
        capfd,
        "interfaces XYZ",
        "Container 'XYZui' is not defined",
        "You can use rapydo interfaces list to get available interfaces",
    )
    exec_command(
        capfd,
        "interfaces list",
        "List of available interfaces:",
        " - mongo",
        " - sqlalchemy",
        " - swagger",
        " - celery",
    )

    exec_command(
        capfd,
        "interfaces sqlalchemy --port XYZ --detach",
        "Invalid value for '--port' / '-p': XYZ is not a valid integer",
    )

    exec_command(
        capfd,
        "interfaces sqlalchemy --detach",
        "Launching interface: sqlalchemyui",
        "docker-compose command: 'run'",
    )
    exec_command(
        capfd,
        "interfaces sqlalchemy --port 123 --detach",
        "Launching interface: sqlalchemyui",
        "docker-compose command: 'run'",
    )

    exec_command(
        capfd,
        "interfaces swagger --port 124 --detach",
        "You can access swaggerui web page here:",
        "http://localhost:124?docExpansion=list&",
        "url=http://localhost:8080/api/specs",
    )

    exec_command(
        capfd,
        "version",
        f"rapydo: \033[1;32m{__version__}",
        f"required rapydo: \033[1;32m{__version__}",
    )

    # docker dump
    exec_command(
        capfd, "dump", "Config dump: docker-compose.yml",
    )

    exec_command(capfd, "upgrade")
    exec_command(
        capfd, "upgrade --path invalid", "Invalid path, cannot upgrade invalid"
    )
    exec_command(capfd, "upgrade --path .gitignore")

    # Test selection with two projects
    exec_command(
        capfd,
        "create justanother --auth postgres --frontend no --current",
        "Project justanother successfully created",
    )

    os.remove(".projectrc")

    exec_command(
        capfd,
        "check -i main --no-git --no-builds",
        "Multiple projects found, please use --project to specify one of the following",
    )

    # Test with zero projects
    with TemporaryRemovePath("projects"):
        os.mkdir("projects")
        exec_command(
            capfd,
            "check -i main --no-git --no-builds",
            "No project found (projects folder is empty?)",
        )
        shutil.rmtree("projects")

    exec_command(
        capfd, "-p first check -i main --no-git --no-builds", "Checks completed",
    )

    # Check invalid and reserved project names
    os.makedirs("projects/invalid_character")
    exec_command(
        capfd,
        "-p invalid_character check -i main --no-git --no-builds",
        "Wrong project name, _ is not a valid character.",
    )
    shutil.rmtree("projects/invalid_character")

    os.makedirs("projects/celery")
    exec_command(
        capfd,
        "-p celery check -i main --no-git --no-builds",
        "You selected a reserved name, invalid project name: celery",
    )
    shutil.rmtree("projects/celery")

    exec_command(
        capfd,
        "-p fourth check -i main --no-git --no-builds",
        "Wrong project fourth",
        "Select one of the following: ",
    )

    # Test init of data folders
    shutil.rmtree("data/logs")
    assert not os.path.isdir("data/logs")
    # Let's restore .projectrc and data/logs
    exec_command(
        capfd, "--project first init", "Project initialized",
    )
    assert os.path.isdir("data/logs")
    exec_command(
        capfd, "check -i main --no-git --no-builds", "Checks completed",
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
        "check -i main",
        "You have unstaged files on do",
        "Untracked files:",
        "submodules/do/new_file",
        f"Obsolete image rapydo/backend:{__version__}",
        "built on ",
        " but changed on ",
        "Update it with: rapydo --service backend pull",
    )

    exec_command(capfd, "verify sqlalchemy", "No container found for backend_1")

    exec_command(
        capfd, "-s invalid start", "No such service: invalid",
    )

    # Let's start with the stack
    exec_command(
        capfd, "start", "docker-compose command: 'up'", "Stack started",
    )

    exec_command(
        capfd,
        "status",
        "docker-compose command: 'ps'",
        # "first_backend_1",
    )

    exec_command(
        capfd, "shell backend --command hostname", "backend-server",
    )

    signal.signal(signal.SIGALRM, handler)
    signal.alarm(2)
    exec_command(
        capfd,
        "shell backend --default-command",
        # "*** RESTful HTTP API ***",
        # "Serving Flask app",
        "Time is up",
    )

    signal.signal(signal.SIGALRM, handler)
    signal.alarm(2)
    exec_command(
        capfd,
        "shell backend",
        # "developer@backend-server:[/code]",
        "Time is up",
    )

    # Testing default users
    exec_command(
        capfd, "shell backend --command whoami", "developer",
    )
    exec_command(
        capfd, "shell frontend --command whoami", "node",
    )
    # No default user for rabbit container
    exec_command(
        capfd, "shell rabbit --command whoami", "root",
    )
    exec_command(
        capfd, "shell postgres --command whoami", "postgres",
    )
    exec_command(
        capfd, "shell neo4j --command whoami", "neo4j",
    )

    exec_command(
        capfd,
        "scale rabbit",
        "Please specify how to scale: SERVICE=NUM_REPLICA",
        "You can also set a DEFAULT_SCALE_RABBIT variable in your .projectrc file",
    )
    exec_command(
        capfd, "scale rabbit=x", "Invalid number of replicas: x",
    )

    exec_command(
        capfd,
        "scale rabbit=2",
        # "Starting first_rabbit_1",
        # "Creating first_rabbit_2",
    )

    with open(".projectrc", "a") as f:
        f.write("\n      DEFAULT_SCALE_RABBIT: 3\n")

    exec_command(
        capfd,
        "scale rabbit",
        # "Starting first_rabbit_1",
        # "Starting first_rabbit_2",
        # "Creating first_rabbit_3",
    )

    exec_command(
        capfd,
        "scale rabbit=1",
        # "Starting first_rabbit_1",
        # "Stopping and removing first_rabbit_2",
        # "Stopping and removing first_rabbit_3",
    )

    exec_command(
        capfd,
        "logs -s backend --tail 10",
        "docker-compose command: 'logs'",
        "backend_1",
    )

    signal.signal(signal.SIGALRM, mock_KeyboardInterrupt)
    signal.alarm(3)
    # Here using main services option
    exec_command(
        capfd,
        "-s backend logs --tail 10 --follow",
        "docker-compose command: 'logs'",
        "Stopped by keyboard",
    )

    # We modified projectrc to contain: DEFAULT_SCALE_RABBIT: 3
    with open(".env") as env:
        content = [line.rstrip("\n") for line in env]
    assert "DEFAULT_SCALE_RABBIT=3" in content

    # Now we set an env varable to change this value:
    os.environ["DEFAULT_SCALE_RABBIT"] = "2"
    exec_command(capfd, "check -i main")
    with open(".env") as env:
        content = [line.rstrip("\n") for line in env]
    assert "DEFAULT_SCALE_RABBIT=3" not in content
    assert "DEFAULT_SCALE_RABBIT=2" in content

    exec_command(capfd, "verify invalid", "Service invalid not detected")
    exec_command(capfd, "verify redis", "Service redis not detected")
    exec_command(capfd, "verify sqlalchemy", "Service sqlalchemy is reachable")

    exec_command(
        capfd,
        "backup neo4j",
        "Neo4j is running and the backup will temporary stop it. "
        "If you want to continue add --force flag",
    )
    exec_command(
        capfd,
        "backup neo4j --force --restart backend --restart rabbit",
        "Starting backup on neo4j...",
        "Backup completed: data/backup/neo4j/",
    )
    exec_command(
        capfd,
        "backup postgres",
        "Starting backup on postgres...",
        "Backup completed: data/backup/postgres/",
    )
    exec_command(
        capfd,
        "backup invalid",
        "invalid choice: invalid. (choose from neo4j, postgres)",
    )

    exec_command(
        capfd, "stop", "Stack stopped",
    )

    exec_command(
        capfd,
        "backup neo4j",
        "Starting backup on neo4j...",
        "Backup completed: data/backup/neo4j/",
    )
    exec_command(
        capfd,
        "backup postgres",
        "The backup procedure requires postgres running, please start your stack",
    )

    exec_command(
        capfd, "restart", "Stack restarted",
    )

    exec_command(
        capfd,
        "-s backend remove --net",
        "Incompatibile options --networks and --service",
    )

    exec_command(
        capfd, "-s backend remove --all", "Incompatibile options --all and --service",
    )

    exec_command(
        capfd, "remove", "docker-compose command: 'stop'", "Stack removed",
    )

    exec_command(
        capfd, "remove --networks", "Stack removed",
    )

    exec_command(
        capfd, "remove --all", "Stack removed",
    )

    exec_command(
        capfd, "shell backend --command hostname", "No container found for backend_1",
    )

    signal.signal(signal.SIGALRM, handler)
    signal.alarm(4)
    exec_command(
        capfd,
        "-s backend start --no-detach",
        # "REST API backend server is ready to be launched",
        "Time is up",
    )

    # This is because after start --no-detach the container in still in exited status
    exec_command(
        capfd,
        "volatile backend --command hostname",
        "Bind for 0.0.0.0:8080 failed: port is already allocated",
    )

    exec_command(
        capfd, "remove --all", "Stack removed",
    )

    exec_command(
        capfd, "volatile backend --command hostname", "backend-server",
    )

    exec_command(
        capfd, "volatile backend --command whoami", "root",
    )
    exec_command(
        capfd,
        "volatile backend -u developer --command whoami",
        "Please remember that users in volatile containers are not mapped on current ",
        "developer",
    )
    exec_command(
        capfd,
        "volatile backend -u invalid --command whoami",
        "Error response from daemon: linux spec user: unable to find user invalid:",
        "no matching entries in passwd file",
    )

    signal.signal(signal.SIGALRM, handler)
    signal.alarm(4)
    exec_command(
        capfd,
        "volatile maintenance",
        # "Maintenance server is up and waiting for connections",
        "Time is up",
    )

    pconf = "projects/first/project_configuration.yaml"

    exec_command(
        capfd,
        "--prod check -i main --no-git --no-builds",
        "The following variables are missing in your configuration",
    )

    exec_command(
        capfd,
        "--prod init -f",
        "Created default .projectrc file",
        "Project initialized",
    )

    exec_command(
        capfd,
        "--prod interfaces swagger --port 124 --detach",
        "You can access swaggerui web page here:",
        "http://localhost:124?docExpansion=list&",
        "url=https://localhost/api/specs",
    )

    exec_command(
        capfd, "--prod -s proxy pull", "Base images pulled from docker hub",
    )

    exec_command(
        capfd, "ssl", "No container found for proxy_1",
    )

    exec_command(
        capfd,
        "ssl --volatile",
        "Creating a self signed SSL certificate",
        "Self signed SSL certificate successfully created",
        # Just to verify that the default does not change
        "Generating DH parameters, 1024 bit long safe prime, generator 2",
    )

    exec_command(
        capfd, "ssl --force", "No container found for proxy_1",
    )
    exec_command(
        capfd, "ssl --chain-file /file", "Invalid chain file (you provided /file)",
    )
    exec_command(
        capfd, "ssl --key-file /file", "Invalid chain file (you provided none)",
    )
    exec_command(
        capfd, f"ssl --chain-file {pconf}", "Invalid key file (you provided none)",
    )
    exec_command(
        capfd,
        f"ssl --chain-file {pconf} --key-file /file",
        "Invalid key file (you provided /file)",
    )
    exec_command(
        capfd,
        "ssl --chain-file {f} --key-file {f}".format(f=pconf),
        "Unable to automatically perform the requested operation",
        "You can execute the following commands by your-self:",
    )

    exec_command(
        capfd, "dhparam", "No container found for proxy_1",
    )


def test_builds(capfd):
    os.remove(".projectrc")

    create_command = "create testbuild --auth postgres --frontend angular"
    create_command += " --service rabbit --add-optionals --current"
    exec_command(
        capfd, create_command, "Project testbuild successfully created",
    )

    # Restore the default project
    exec_command(
        capfd, "-p testbuild init --force", "Project initialized",
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
        "-s rabbit build",
        "No such file or directory: ",
        "projects/testbuild/builds/rabbit/Dockerfile",
    )

    # Empty Dockerfile
    with open("projects/testbuild/builds/rabbit/Dockerfile", "w+") as f:
        pass
    exec_command(
        capfd,
        "-s rabbit build",
        "Build failed, is ",
        "projects/testbuild/builds/rabbit/Dockerfile empty?",
    )

    # Missing base image
    with open("projects/testbuild/builds/rabbit/Dockerfile", "w+") as f:
        f.write("RUN ls")
    exec_command(
        capfd,
        "-s rabbit build",
        "No base image found ",
        "projects/testbuild/builds/rabbit/Dockerfile, unable to build",
    )

    # Not a RAPyDo child
    with open("projects/testbuild/builds/rabbit/Dockerfile", "w+") as f:
        f.write("FROM ubuntu")
    exec_command(
        capfd, "-s rabbit build", "No custom images to build",
    )

    # Invalid RAPyDo template
    with open("projects/testbuild/builds/rabbit/Dockerfile", "w+") as f:
        f.write("FROM rapydo/invalid")
    exec_command(
        capfd,
        "-s rabbit build",
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
        "-s rabbit build",
        "Successfully built",
        f"Successfully tagged testbuild/rabbit:{__version__}",
        "Custom images built",
    )

    exec_command(
        capfd, "ancestors XYZ", "No child found for XYZ",
    )

    dock = Dock()
    img = dock.images().pop(0)
    # sha256:c1a845de80526fcab136f9fab5f83BLABLABLABLABLA
    img_id = dock.image_info(img).get("Id")
    # => c1a845de8052
    img_id = img_id[7:19]
    exec_command(
        capfd,
        f"ancestors {img_id}",
        f"Finding all children and (grand)+ children of {img_id}",
    )

    # sha256:c1a845de80526fcab136f9fab5f83BLABLABLABLABLA
    img_id = dock.image_info(f"rapydo/rabbitmq:{__version__}").get("Id")
    # => c1a845de8052
    img_id = img_id[7:19]
    # rapydo/rabbitmq has a child: testbuild/rabbit just created
    exec_command(
        capfd,
        f"ancestors {img_id}",
        f"Finding all children and (grand)+ children of {img_id}",
        "testbuild/rabbit",
    )

    # Rebuild core rabbit image => custom rabbit is now obsolete
    # Please note the use of the first project.
    # This way we prevent to rebuilt the custom image of testbuild
    # This simulate a pull updating a core image making the custom image obsolete
    exec_command(
        capfd,
        "-p first -s rabbit build --core",
        "Core images built",
        "No custom images to build",
    )
    exec_command(
        capfd,
        "check -i main --no-git",
        f"Obsolete image testbuild/rabbit:{__version__}",
        "built on ",
        " that changed on ",
        "Update it with: rapydo --service rabbit build",
    )

    # rabbit images has no longer any child because it is just rebuilt
    exec_command(
        capfd,
        f"ancestors {img_id}",
        f"Finding all children and (grand)+ children of {img_id}",
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
        "-s rabbit,rabbit2 build",
        "Cannot determine build priority between rabbit and rabbit2",
        "Removed redundant services from ['rabbit', 'rabbit2'] -> ['rabbit2']",
    )

    # Let's test builds with running containers
    exec_command(capfd, "-s rabbit start")

    you_asked = f"You asked to build testbuild/rabbit:{__version__}"
    but_running = "but the following containers are running: rabbit"
    do_you_want_to = "Do you want to continue? y/n:"

    exec_command(
        capfd,
        "-s rabbit build",
        you_asked,
        but_running,
        do_you_want_to,
        "Unknown response invalid, respond yes or no",
        "Build aborted",
        input_text="invalid\nno\n",
    )

    exec_command(
        capfd,
        "-s rabbit build",
        you_asked,
        but_running,
        do_you_want_to,
        "Build aborted",
        input_text="no\n",
    )
    exec_command(
        capfd,
        "-s rabbit build",
        you_asked,
        but_running,
        do_you_want_to,
        "Build aborted",
        input_text="n\n",
    )
    exec_command(
        capfd,
        "-s rabbit build",
        you_asked,
        but_running,
        do_you_want_to,
        "Build aborted",
        input_text="N\n",
    )
    exec_command(
        capfd,
        "-s rabbit build",
        you_asked,
        but_running,
        do_you_want_to,
        "Build aborted",
        input_text="NO\n",
    )
    exec_command(
        capfd,
        "-s rabbit build",
        you_asked,
        but_running,
        do_you_want_to,
        "Successfully built",
        input_text="y\n",
    )
    exec_command(
        capfd,
        "-s rabbit build",
        you_asked,
        but_running,
        do_you_want_to,
        "Successfully built",
        input_text="yes\n",
    )
    exec_command(
        capfd,
        "-s rabbit build",
        you_asked,
        but_running,
        do_you_want_to,
        "Successfully built",
        input_text="Y\n",
    )
    exec_command(
        capfd,
        "-s rabbit build",
        you_asked,
        but_running,
        do_you_want_to,
        "Successfully built",
        input_text="YES\n",
    )
    exec_command(
        capfd, "-s rabbit build --yes", "Successfully built",
    )

    exec_command(capfd, "remove")

    # Restore the default project
    exec_command(
        capfd, "-p first init --force", "Project initialized",
    )


def test_extend(capfd):
    # base project is --auth postgres --frontend angular
    # the ext one is --auth neo4j --frontend angular
    exec_command(
        capfd,
        "create base --auth neo4j --frontend no --current",
        "Project folder already exists: projects",
        "Project base successfully created",
    )

    exec_command(
        capfd,
        "create new --extend new --auth neo4j --frontend no --current",
        "A project cannot extend itself",
    )
    exec_command(
        capfd,
        "create new --extend doesnotexist --auth neo4j --frontend no --current",
        "Invalid extend value: project doesnotexist not found",
    )

    create_command = "create ext --extend base"
    create_command += " --auth neo4j --frontend angular"
    create_command += " --current --service rabbit"
    exec_command(
        capfd,
        create_command,
        "Project folder already exists: projects",
        "Project ext successfully created",
    )

    exec_command(
        capfd, "-p ext init --force", "Project initialized",
    )
    exec_command(
        capfd, "-p ext check -i main --no-git --no-builds", "Checks completed",
    )


def test_services_activation(capfd):

    os.remove(".projectrc")

    # Test services activation from create --service
    services = [
        "postgres",
        "mysql",
        "neo4j",
        "mongo",
        "rabbit",
        "redis",
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
            serv_opt = f"--service {service}"

        exec_command(
            capfd,
            "create testservices {opt} --auth {auth} {service}".format(
                opt=opt, auth=auth, service=serv_opt
            ),
            "Project testservices successfully created",
        )
        if service == "mysql":
            service = ["mariadb"]
        elif service == "celery":
            service = ["celery", "celeryui", "rabbit"]
        else:
            service = [service]

        exec_command(
            capfd,
            "-p testservices list services",
            "List of active services:",
            *service,
        )


def test_celery_activation(capfd):

    # Previous test already deleted the .project and no init is execute afterwards
    # => .project does not exist and cannot be removed
    # os.remove(".projectrc")

    opt = "--frontend no --current --force --auth neo4j"
    project_configuration = "projects/testcelery/project_configuration.yaml"

    def test_celery_configuration(services_list, broker, backend):

        services = "--service celery"
        if services_list:
            for service in services_list:
                services += f" --service {service}"

        exec_command(
            capfd,
            f"create testcelery {opt} {services}",
            "Project testcelery successfully created",
        )

        with open(project_configuration) as f:
            lines = f.readlines()
        assert next(x.strip() for x in lines if "CELERY_BROKER" in x).endswith(broker)
        assert next(x.strip() for x in lines if "CELERY_BACKEND" in x).endswith(backend)

    test_celery_configuration([], "RABBIT", "RABBIT")
    test_celery_configuration(["rabbit"], "RABBIT", "RABBIT")
    test_celery_configuration(["redis"], "REDIS", "REDIS")
    test_celery_configuration(["mongo"], "RABBIT", "MONGODB")
    test_celery_configuration(["rabbit", "redis"], "RABBIT", "REDIS")
    test_celery_configuration(["rabbit", "mongo"], "RABBIT", "MONGODB")
    test_celery_configuration(["redis", "mongo"], "REDIS", "REDIS")
    test_celery_configuration(["rabbit", "redis", "mongo"], "RABBIT", "REDIS")


def test_rabbit_invalid_characters(capfd):

    create_command = "create testinvalid --auth postgres --frontend angular"
    create_command += " --service rabbit --env RABBITMQ_PASSWORD=invalid£password"
    create_command += " --current --force"
    exec_command(
        capfd, create_command, "Project testinvalid successfully created",
    )

    informative = "Some special characters, including £ § ” ’, are not allowed "
    informative = "because make RabbitMQ crash at startup"

    exec_command(
        capfd,
        "-p testinvalid init --force",
        "Not allowed characters found in RABBITMQ_PASSWORD.",
        informative,
    )

    shutil.rmtree("projects/testinvalid")

    # Restore the default project
    exec_command(
        capfd, "-p first init --force", "Project initialized",
    )


def test_install(capfd):

    with TemporaryRemovePath("submodules/do"):
        exec_command(
            capfd, "install", "missing as submodules/do. You should init your project",
        )

    # I hope that one day this test will fail! :-)
    exec_command(capfd, "install 1.0", "Invalid version")

    exec_command(capfd, "install auto")

    r = gitter.get_repo("submodules/do")
    gitter.switch_branch(r, "0.7.3")

    exec_command(
        capfd, "install", f"Controller repository switched to {__version__}",
    )

    exec_command(capfd, "install")

    exec_command(capfd, "install --no-editable")

    # This is the very last command... installing an old version!
    exec_command(capfd, "install --no-editable 0.7.2")

    # This test will change the required version
    pconf = "projects/first/project_configuration.yaml"

    # Read and change the content
    fin = open(pconf)
    data = fin.read()
    data = data.replace(f"rapydo: {__version__}", "rapydo: 0.7.3")
    fin.close()
    # Write the new content
    fin = open(pconf, "wt")
    fin.write(data)
    fin.close()

    exec_command(
        capfd,
        "version",
        f"This project is not compatible with rapydo version {__version__}",
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
        "version",
        f"This project is not compatible with rapydo version {__version__}",
        "Please upgrade rapydo to version 99.99.99 or modify this project",
    )


# Some final tests
def test_lastest(capfd):

    exec_command(
        capfd,
        "create latest --auth postgres --frontend no --current --force",
        "Project latest successfully created",
    )

    folder = os.getcwd()
    # Tests from a subfolder
    os.chdir("projects")
    exec_command(
        capfd,
        "-p latest check -i main --no-git --no-builds",
        "You are not in the main folder, please change your working dir",
        "Found a valid parent folder:",
        "Suggested command: cd ..",
    )

    os.chdir("latest")
    exec_command(
        capfd,
        "-p latest check -i main --no-git --no-builds",
        "You are not in the main folder, please change your working dir",
        "Found a valid parent folder:",
        "Suggested command: cd ../..",
    )

    # Tests from outside the folder
    os.chdir(tempfile.gettempdir())
    exec_command(
        capfd,
        "check -i main",
        "You are not in a git repository",
        "Please note that this command only works from inside a rapydo-like repository",
        "Verify that you are in the right folder, now you are in:",
    )

    os.chdir(folder)
