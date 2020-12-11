import os
import shutil
import signal
import time
from datetime import datetime

from git import Repo

from controller import __version__, gitter
from controller.dockerizing import Dock
from tests import (
    TemporaryRemovePath,
    create_project,
    exec_command,
    mock_KeyboardInterrupt,
    signal_handler,
)


def test_all(capfd):

    create_project(
        capfd=capfd,
        name="first",
        auth="postgres",
        frontend="angular",
        services=["rabbit", "neo4j"],
        extra="--env CUSTOMVAR1=mycustomvalue --env CUSTOMVAR2=mycustomvalue",
        init=True,
    )

    path = "projects/first/backend/endpoints/xyz.py"
    test_path = "projects/first/backend/tests/test_endpoints_xyz.py"
    assert not os.path.exists(path)
    assert not os.path.exists(test_path)
    exec_command(
        capfd,
        "add endpoint xyz --add-tests",
        f"Endpoint created: {path}",
        f"Tests scaffold created: {test_path}",
    )
    exec_command(
        capfd,
        "add endpoint xyz",
        f"{path} already exists",
    )
    exec_command(
        capfd,
        "add --force endpoint xyz",
        f"Endpoint created: {path}",
    )
    assert os.path.isfile(path)
    assert os.path.isfile(test_path)

    path = "projects/first/backend/tasks/xyz.py"
    assert not os.path.exists(path)
    exec_command(
        capfd,
        "add task xyz --add-tests",
        f"Task created: {path}",
        "Tests for tasks not implemented yet",
    )
    exec_command(
        capfd,
        "add task xyz",
        f"{path} already exists",
    )
    exec_command(
        capfd,
        "add --force task xyz",
        f"Task created: {path}",
    )
    assert os.path.isfile(path)

    path = "projects/first/frontend/app/components/xyz"
    test_path = "projects/first/frontend/app/components/xyz/xyz.spec.ts"
    assert not os.path.exists(path)
    assert not os.path.exists(os.path.join(path, "xyz.ts"))
    assert not os.path.exists(os.path.join(path, "xyz.html"))
    exec_command(
        capfd,
        "add component xyz --add-tests",
        "Added import { XyzComponent } from '@app/components/xyz/xyz'; to module ",
        "Added XyzComponent to module declarations",
        f"Component created: {path}",
        f"Tests scaffold created: {test_path}",
    )

    assert os.path.isdir(path)
    assert os.path.isfile(os.path.join(path, "xyz.ts"))
    assert os.path.isfile(os.path.join(path, "xyz.html"))
    exec_command(
        capfd,
        "add component xyz",
        f"{path}/xyz.ts already exists",
    )
    exec_command(
        capfd,
        "add --force component xyz",
        f"Component created: {path}",
    )
    shutil.rmtree(path)
    exec_command(
        capfd,
        "add component xyz",
        "Import already included in module file",
        "Added XyzComponent to module declarations",
        f"Component created: {path}",
    )

    exec_command(
        capfd,
        "add component sink",
        "Added route to module declarations",
        "Added SinkComponent to module declarations",
    )

    path = "projects/first/frontend/app/services"
    assert not os.path.exists(path)
    assert not os.path.exists(os.path.join(path, "xyz.ts"))
    exec_command(
        capfd,
        "add service xyz --add-tests",
        "Added import { XyzService } from '@app/services/xyz'; to module file",
        "Added XyzService to module declarations",
        f"Service created: {path}",
        "Tests for services not implemented yet",
    )
    assert os.path.isdir(path)
    assert os.path.isfile(os.path.join(path, "xyz.ts"))
    exec_command(
        capfd,
        "add service xyz",
        f"{path}/xyz.ts already exists",
    )
    exec_command(
        capfd,
        "add --force service xyz",
        f"Service created: {path}",
    )
    os.remove(f"{path}/xyz.ts")
    exec_command(
        capfd,
        "add service xyz",
        "Import already included in module file",
        "Added XyzService to module declarations",
        f"Service created: {path}",
    )

    path = "projects/first/frontend/integration/app_mypath_my_id.spec.ts"
    assert not os.path.exists(path)
    exec_command(
        capfd,
        "add integration_test app/mypath/:my_id --add-tests",
        "Add integration_test does not support --add-tests flag",
    )

    exec_command(
        capfd,
        "add integration_test app/mypath/:my_id",
        f"Integration test created: {path}",
    )
    exec_command(
        capfd,
        "add integration_test app/mypath/:my_id",
        f"{path} already exists",
    )
    # Here a little variant, by adding a leading /
    exec_command(
        capfd,
        "add --force integration_test /app/mypath/:my_id",
        f"Integration test created: {path}",
    )
    assert os.path.isfile(path)

    exec_command(
        capfd,
        "add abc xyz",
        "invalid choice: abc. "  # Note no command
        "(choose from endpoint, task, component, service, integration_test)",
    )

    # Basic pull
    exec_command(
        capfd,
        "-s xxx pull",
        "Invalid service name: xxx",
    )
    exec_command(
        capfd,
        "pull",
        "Base images pulled from docker hub",
    )

    # Skipping main because we are on a fake git repository
    exec_command(
        capfd,
        "update -i main",
        "All updated",
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
        capfd,
        "check -i main",
        "Checks completed",
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
        capfd,
        "list submodules",
        "List of submodules:",
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
        capfd,
        "dump",
        "Config dump: docker-compose.yml",
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
        capfd,
        "-p first check -i main --no-git --no-builds",
        "Checks completed",
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
        capfd,
        "--project first init",
        "Project initialized",
    )
    assert os.path.isdir("data/logs")
    exec_command(
        capfd,
        "check -i main --no-git --no-builds",
        "Checks completed",
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
        "Update it with: rapydo --services backend pull",
    )

    with open(".pre-commit-config.yaml", "a") as a_file:
        a_file.write("\n")
        a_file.write("# new line")

    exec_command(
        capfd,
        "check -i main",
        ".pre-commit-config.yaml changed, "
        "please execute rapydo upgrade --path .pre-commit-config.yaml",
    )

    exec_command(
        capfd, "verify --no-tty sqlalchemy", "No container found for backend_1"
    )

    exec_command(
        capfd,
        "-s invalid start",
        "No such service: invalid",
    )

    exec_command(capfd, "diagnostic http://localhost", "http schema not supported")
    exec_command(
        capfd,
        "diagnostic https://nolocalhost",
        "Host https://nolocalhost is unreachable",
    )
    exec_command(
        capfd, "diagnostic nolocalhost", "Host https://nolocalhost is unreachable"
    )

    # Let's start with the stack
    exec_command(
        capfd,
        "-e CRONTAB_ENABLE=1 start",
        "docker-compose command: 'up'",
        "Stack started",
    )

    exec_command(
        capfd,
        "-s backend -e CRONTAB_ENABLE=1 start --force",
        "docker-compose command: 'up'",
        "Stack started",
    )

    exec_command(
        capfd,
        "status",
        "docker-compose command: 'ps'",
        # "first_backend_1",
    )

    # Added for GitHub Actions
    exec_command(
        capfd,
        "shell backend hostname",
        "the input device is not a TTY",
    )

    # --no-tty is needed on GitHub Actions
    exec_command(
        capfd,
        "shell --no-tty backend --command hostname",
        "Deprecated use of --command",
    )
    exec_command(
        capfd,
        "shell --no-tty backend --command 'hostname --short'",
        "Deprecated use of --command",
    )

    exec_command(
        capfd,
        "shell --no-tty backend hostname",
        "backend-server",
    )

    signal.signal(signal.SIGALRM, signal_handler)
    signal.alarm(2)
    exec_command(
        capfd,
        "shell --no-tty backend --default-command",
        # "*** RESTful HTTP API ***",
        # "Serving Flask app",
        "Time is up",
    )

    # This can't work on GitHub Actions due to the lack of tty
    # signal.signal(signal.SIGALRM, handler)
    # signal.alarm(2)
    # exec_command(
    #     capfd,
    #     "shell --no-tty backend",
    #     # "developer@backend-server:[/code]",
    #     "Time is up",
    # )

    # Testing default users
    exec_command(
        capfd,
        "shell --no-tty backend whoami",
        "developer",
    )
    exec_command(
        capfd,
        "shell --no-tty frontend whoami",
        "node",
    )
    # No default user for rabbit container
    exec_command(
        capfd,
        "shell --no-tty rabbit whoami",
        "root",
    )
    exec_command(
        capfd,
        "shell --no-tty postgres whoami",
        "postgres",
    )
    exec_command(
        capfd,
        "shell --no-tty neo4j whoami",
        "neo4j",
    )

    exec_command(
        capfd,
        "scale rabbit",
        "Please specify how to scale: SERVICE=NUM_REPLICA",
        "You can also set a DEFAULT_SCALE_RABBIT variable in your .projectrc file",
    )
    exec_command(
        capfd,
        "-e DEFAULT_SCALE_RABBIT=2 scale rabbit",
        # "Starting first_rabbit_1",
        # "Creating first_rabbit_2",
    )
    exec_command(
        capfd,
        "scale rabbit=x",
        "Invalid number of replicas: x",
    )

    exec_command(
        capfd,
        "scale rabbit=2",
        # "Starting first_rabbit_1",
        # "Starting first_rabbit_2",
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

    # Backend logs are never timestamped

    exec_command(
        capfd,
        "logs -s backend --tail 10 --no-color",
        "docker-compose command: 'logs'",
        "backend_1       | Development mode",
        "Found no cronjob to be enabled, skipping crontab setup",
    )

    with open("projects/first/backend/cron/hello-world.cron", "w+") as f:
        f.write("* * * * * echo 'Hello world' >> /var/log/cron.log 2>&1\n")
        f.write("\n")

    # After the restart the cron enabled will be tested again
    # Test is below to wait the container restart
    exec_command(
        capfd,
        "-s backend restart",
        "Stack restarted",
    )

    now = datetime.now()
    timestamp = now.strftime("%Y-%m-%dT")

    # Frontend logs are timestamped
    exec_command(
        capfd,
        "-s frontend logs --tail 10 --no-color",
        "docker-compose command: 'logs'",
        f"frontend_1      | {timestamp}",
    )

    # With multiple services logs are not timestamped
    exec_command(
        capfd,
        "-s frontend,backend logs --tail 10 --no-color",
        "docker-compose command: 'logs'",
        "backend_1       | Development mode",
        "frontend_1      | Merging files...",
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

    # Test again the cron enabling
    exec_command(
        capfd,
        "logs -s backend --tail 10 --no-color",
        "docker-compose command: 'logs'",
        "backend_1       | Development mode",
        "backend_1       | Enabling cron...",
        "backend_1       | Cron enabled",
        # this is the output of crontab -l that verifies the cronjob installation
        "* * * * * echo 'Hello world'",
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

    exec_command(capfd, "verify --no-tty invalid", "Service invalid not detected")
    exec_command(capfd, "verify --no-tty redis", "Service redis not detected")
    exec_command(capfd, "verify --no-tty sqlalchemy", "Service sqlalchemy is reachable")

    # This will initialize postgres
    exec_command(capfd, "shell --no-tty backend 'restapi init'")
    # And this will also initialize neo4j (what a trick!)
    # Temporary change AUTH_SERVICE from postgres to neo4j
    exec_command(capfd, "-e AUTH_SERVICE=neo4j -s backend start")
    exec_command(capfd, "shell --no-tty backend 'restapi init'")
    # Restore correct AUTH_SERVICE
    exec_command(capfd, "-s backend start")

    # Backup command
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
    # This is to verify that --force restarted neo4j
    exec_command(
        capfd,
        "backup neo4j",
        "Neo4j is running and the backup will temporary stop it. "
        "If you want to continue add --force flag",
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
        capfd,
        "stop",
        "Stack stopped",
    )

    exec_command(
        capfd,
        "backup neo4j",
        "Starting backup on neo4j...",
        "Backup completed: data/backup/neo4j/",
    )

    exec_command(capfd, "-s neo4j start")

    exec_command(
        capfd,
        "backup postgres",
        "The backup procedure requires postgres running, please start your stack",
    )

    # Restore command
    exec_command(
        capfd, "restore neo4j", "Please specify one of the following backup:", ".dump"
    )
    exec_command(
        capfd,
        "restore postgres",
        "Please specify one of the following backup:",
        ".sql.gz",
    )
    exec_command(
        capfd,
        "restore neo4j invalid",
        "Invalid backup file, data/backup/neo4j/invalid does not exist",
    )
    exec_command(
        capfd,
        "restore postgres invalid",
        "Invalid backup file, data/backup/postgres/invalid does not exist",
    )

    with TemporaryRemovePath("data/backup"):
        exec_command(
            capfd,
            "restore postgres",
            "No backup found, the following folder "
            "does not exist: data/backup/postgres",
        )

        exec_command(
            capfd,
            "restore neo4j",
            "No backup found, the following folder "
            "does not exist: data/backup/neo4j",
        )

    with TemporaryRemovePath("data/backup/neo4j"):
        exec_command(
            capfd,
            "restore neo4j",
            "No backup found, the following folder does not exist: data/backup/neo4j",
        )
        exec_command(
            capfd,
            "restore postgres",
            "Please specify one of the following backup:",
        )

        os.mkdir("data/backup/neo4j")

        exec_command(
            capfd,
            "restore neo4j",
            "No backup found, data/backup/neo4j is empty",
        )

        open("data/backup/neo4j/test.gz", "a").close()

        exec_command(
            capfd,
            "restore neo4j",
            "No backup found, data/backup/neo4j is empty",
        )

        open("data/backup/neo4j/test.dump", "a").close()

        exec_command(
            capfd,
            "restore neo4j",
            "Please specify one of the following backup:",
            "test.dump",
        )

        os.remove("data/backup/neo4j/test.gz")
        os.remove("data/backup/neo4j/test.dump")

    # Test restore on neo4j (required neo4j to be down)
    files = os.listdir("data/backup/neo4j")
    files = [f for f in files if f.endswith(".dump")]
    files.sort()
    neo4j_dump_file = files[-1]

    files = os.listdir("data/backup/postgres")
    files = [f for f in files if f.endswith(".sql.gz")]
    files.sort()
    postgres_dump_file = files[-1]

    # You should somehow verify output from (or similar):
    # command = "bin/cypher-shell \"match (u: User) return u.email\""

    cypher = "shell --no-tty neo4j 'bin/cypher-shell"
    # Here we test the restore procedure:
    # 1) verify some data in the database
    exec_command(
        capfd,
        f'{cypher} "match (r: Role) return r.name, r.description"\'',
        '"normal_user", "User"',
    )

    # 2) Modify such data
    exec_command(capfd, f'{cypher} "match (r: Role) SET r.description = r.name"\'')
    exec_command(
        capfd,
        f'{cypher} "match (r: Role) return r.name, r.description"\'',
        '"normal_user", "normal_user"',
    )
    exec_command(capfd, "-s neo4j remove")
    # 3) restore the dump
    exec_command(
        capfd,
        f"restore neo4j {neo4j_dump_file}",
        "Starting restore on neo4j...",
        "Done: ",
        f"Restore from data/backup/neo4j/{neo4j_dump_file} completed",
    )

    # Tuning command with neo4j container OFF
    exec_command(
        capfd,
        "tuning neo4j",
        "Number of CPU(s): ",
        "Amount of RAM: ",
        "Suggested settings:",
        "Use 'dbms.memory.heap.max_size' as NEO4J_HEAP_SIZE",
        "Use 'dbms.memory.pagecache.size' as NEO4J_PAGECACHE_SIZE",
        "Memory settings recommendation from neo4j-admin memrec:",
        "Based on the above, the following memory settings are recommended:",
        "dbms.memory.heap.initial_size=",
        "dbms.memory.heap.max_size=",
        "dbms.memory.pagecache.size=",
        "Total size of lucene indexes in all databases:",
        "Total size of data and native indexes in all databases:",
    )

    exec_command(capfd, "-s neo4j start")
    # 4) verify data match again point 1 (restore completed)
    # postponed because neo4j needs time to start...

    # Postgres restore not allowed if container is not running
    exec_command(
        capfd,
        f"restore postgres {postgres_dump_file}",
        "The restore procedure requires postgres running, please start your stack",
    )

    # Tuning command with neo4j container ON
    exec_command(
        capfd,
        "tuning neo4j",
        "Number of CPU(s): ",
        "Amount of RAM: ",
        "Suggested settings:",
        "Use 'dbms.memory.heap.max_size' as NEO4J_HEAP_SIZE",
        "Use 'dbms.memory.pagecache.size' as NEO4J_PAGECACHE_SIZE",
        "Memory settings recommendation from neo4j-admin memrec:",
        "Based on the above, the following memory settings are recommended:",
        "dbms.memory.heap.initial_size=",
        "dbms.memory.heap.max_size=",
        "dbms.memory.pagecache.size=",
        "Total size of lucene indexes in all databases:",
        "Total size of data and native indexes in all databases:",
    )
    exec_command(
        capfd,
        "tuning postgres",
        "Number of CPU(s): ",
        "Amount of RAM: ",
        "Suggested settings:",
        "POSTGRES_SHARED_BUFFERS",
        "POSTGRES_EFFECTIVE_CACHE_SIZE",
        "POSTGRES_MAINTENANCE_WORK_MEM",
        "POSTGRES_MAX_WORKER_PROCESSES",
    )
    exec_command(
        capfd,
        "tuning backend",
        "Number of CPU(s): ",
        "Amount of RAM: ",
        "Suggested settings:",
        "GUNICORN_MAX_NUM_WORKERS",
    )

    exec_command(
        capfd,
        "restart",
        "Stack restarted",
    )

    exec_command(
        capfd,
        f"restore neo4j {neo4j_dump_file}",
        "Neo4j is running and the restore will temporary stop it.",
        "If you want to continue add --force flag",
    )

    exec_command(
        capfd,
        f"restore neo4j {neo4j_dump_file} --force --restart backend",
        "Starting restore on neo4j...",
        "Done: ",
        f"Restore from data/backup/neo4j/{neo4j_dump_file} completed",
    )

    psql = "shell --no-tty postgres 'psql -U sqluser -d SQL_API -c"
    # Here we test the restore procedure:
    # 1) verify some data in the database
    exec_command(
        capfd,
        f'{psql} "select name, description from role"\'',
        " normal_user | User",
    )
    # 2) Modify such data
    exec_command(
        capfd,
        f'{psql} "update role SET description=name"\'',
    )
    exec_command(
        capfd,
        f'{psql} "select name, description from role"\'',
        " normal_user | normal_user",
    )
    # 3) restore the dump
    exec_command(
        capfd,
        f"restore postgres {postgres_dump_file}",
        "Starting restore on postgres...",
        "CREATE DATABASE",
        "ALTER DATABASE",
        f"Restore from data/backup/postgres/{postgres_dump_file} completed",
    )

    # 4) verify data match again point 1 (restore completed)
    exec_command(
        capfd,
        f'{psql} "select name, description from role"\'',
        " normal_user | User",
    )

    # This is postponed from one hundred lines above
    # 4) verify data match again point 1 (restore completed)
    exec_command(
        capfd,
        f'{cypher} "match (r: Role) return r.name, r.description"\'',
        '"normal_user", "User"',
    )

    # Test tuning neo4j with container already running
    exec_command(
        capfd,
        "tuning neo4j",
        "Number of CPU(s): ",
        "Amount of RAM: ",
        "Suggested settings:",
        "Use 'dbms.memory.heap.max_size' as NEO4J_HEAP_SIZE",
        "Use 'dbms.memory.pagecache.size' as NEO4J_PAGECACHE_SIZE",
    )

    exec_command(
        capfd,
        "-s backend remove --net",
        "Incompatibile options --networks and --service",
    )

    exec_command(
        capfd,
        "-s backend remove --all",
        "Incompatibile options --all and --service",
    )

    exec_command(
        capfd,
        "remove",
        "docker-compose command: 'stop'",
        "Stack removed",
    )

    exec_command(
        capfd,
        "remove --networks",
        "Stack removed",
    )

    exec_command(
        capfd,
        "remove --all",
        "Stack removed",
    )

    exec_command(
        capfd,
        "shell --no-tty backend hostname",
        "No container found for backend_1",
    )

    signal.signal(signal.SIGALRM, signal_handler)
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
        "volatile backend hostname",
        "Bind for 0.0.0.0:8080 failed: port is already allocated",
    )

    exec_command(
        capfd,
        "remove --all",
        "Stack removed",
    )

    exec_command(
        capfd,
        "volatile backend --command hostname",
        "Deprecated use of --command",
    )
    exec_command(
        capfd,
        "volatile backend --command 'hostname --short'",
        "Deprecated use of --command",
    )

    exec_command(
        capfd,
        "volatile backend hostname",
        "backend-server",
    )

    exec_command(
        capfd,
        "volatile backend whoami",
        "root",
    )
    exec_command(
        capfd,
        "volatile backend -u developer whoami",
        "Please remember that users in volatile containers are not mapped on current ",
        "developer",
    )
    exec_command(
        capfd,
        "volatile backend -u invalid whoami",
        "Error response from daemon:",
        "unable to find user invalid:",
        "no matching entries in passwd file",
    )

    signal.signal(signal.SIGALRM, signal_handler)
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
        "https://localhost:124?docExpansion=list&",
        "url=https://localhost/api/specs",
    )

    # --all is useless here... added just to include the parameter in some tests.
    # A true test on such parameter would be quite complicated...
    exec_command(
        capfd,
        "--prod -s proxy pull --all",
        "Images pulled from docker hub",
    )

    exec_command(
        capfd,
        "ssl",
        "No container found for proxy_1",
    )

    # Before creating SSL certificates, neo4j and rabbit should not be able to start
    exec_command(
        capfd,
        "volatile neo4j",
        "SSL mandatory file not found: /ssl/real/fullchain1.pem",
    )

    exec_command(
        capfd,
        "volatile rabbit",
        "SSL mandatory file not found: /ssl/real/fullchain1.pem",
    )

    exec_command(
        capfd,
        "ssl --volatile",
        "Creating a self signed SSL certificate",
        "Self signed SSL certificate successfully created",
        # Just to verify that the default does not change
        "Generating DH parameters, 1024 bit long safe prime, generator 2",
    )

    # Start neo4j and rabbit to verify certificate creation while services are running
    exec_command(
        capfd,
        "--prod -s rabbit,neo4j start",
    )

    # ARGHHH!!! But it is needed because the next command need rabbit already started
    # And it takes some time to make the server up and running
    # Otherwise will fail with:
    # Error: unable to perform an operation on node 'rabbit@rabbit'.
    # Please see diagnostics information and suggestions below.
    time.sleep(10)

    exec_command(
        capfd,
        # --no-tty is needed on GitHub Actions
        # to be able to execute commands on the running containers
        "ssl --volatile --no-tty",
        "Creating a self signed SSL certificate",
        "Self signed SSL certificate successfully created",
        "Neo4j is running, but it will reload the certificate by itself",
        "RabbitMQ is running, executing command to refresh the certificate",
        "New certificate successfully installed",
    )
    # Shutoff services, only started to verify certificate creation
    exec_command(
        capfd,
        "-s rabbit,neo4j remove",
    )

    exec_command(
        capfd,
        "ssl --force",
        "No container found for proxy_1",
    )
    exec_command(
        capfd,
        "ssl --chain-file /file",
        "Invalid chain file (you provided /file)",
    )
    exec_command(
        capfd,
        "ssl --key-file /file",
        "Invalid chain file (you provided none)",
    )
    exec_command(
        capfd,
        f"ssl --chain-file {pconf}",
        "Invalid key file (you provided none)",
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
        capfd,
        "dhparam",
        "No container found for proxy_1",
    )

    # def test_builds(capfd):
    os.remove(".projectrc")

    create_command = "create testbuild --auth postgres --frontend angular"
    create_command += " --service rabbit --add-optionals --current"
    exec_command(
        capfd,
        create_command,
        "Project testbuild successfully created",
    )

    # Restore the default project
    exec_command(
        capfd,
        "-p testbuild init --force",
        "Project initialized",
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
        capfd,
        "-s rabbit build",
        "No custom images to build",
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
        capfd,
        "ancestors XYZ",
        "No child found for XYZ",
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
        "Update it with: rapydo --services rabbit build",
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
        "Removed redundant builds from ['rabbit', 'rabbit2'] -> ['rabbit2']",
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
        capfd,
        "-s rabbit build --yes",
        "Successfully built",
    )

    exec_command(capfd, "remove")

    # Restore the default project
    exec_command(
        capfd,
        "-p first init --force",
        "Project initialized",
    )

    # def test_extend(capfd):
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
        capfd,
        "-p ext init --force",
        "Project initialized",
    )
    exec_command(
        capfd,
        "-p ext check -i main --no-git --no-builds",
        "Checks completed",
    )

    # def test_services_activation(capfd):

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
            services = ["mariadb"]
        elif service == "celery":
            services = ["celery", "celeryui", "rabbit"]
        else:
            services = [service]

        exec_command(
            capfd,
            "-p testservices list services",
            "List of active services:",
            *services,
        )

    # def test_celery_activation(capfd):

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

    # def test_rabbit_invalid_characters(capfd):

    create_command = "create testinvalid --auth postgres --frontend angular"
    create_command += " --service rabbit --env RABBITMQ_PASSWORD=invalid£password"
    create_command += " --current --force"
    exec_command(
        capfd,
        create_command,
        "Project testinvalid successfully created",
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
        capfd,
        "-p first init --force",
        "Project initialized",
    )

    # def test_install(capfd):

    with TemporaryRemovePath("submodules/do"):
        exec_command(
            capfd,
            "install",
            "missing as submodules/do. You should init your project",
        )

    # I hope that one day this test will fail! :-)
    exec_command(capfd, "install 1.0", "Invalid version")

    exec_command(capfd, "install auto")

    r = gitter.get_repo("submodules/do")
    gitter.switch_branch(r, "0.7.6")

    exec_command(
        capfd,
        "install",
        f"Controller repository switched to {__version__}",
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
    data = data.replace(f'rapydo: "{__version__}"', 'rapydo: "0.7.6"')
    fin.close()
    # Write the new content
    fin = open(pconf, "wt")
    fin.write(data)
    fin.close()

    exec_command(
        capfd,
        "version",
        f"This project is not compatible with rapydo version {__version__}",
        "Please downgrade rapydo to version 0.7.6 or modify this project",
    )

    # Read and change the content
    fin = open(pconf)
    data = fin.read()
    data = data.replace('rapydo: "0.7.6"', 'rapydo: "99.99.99"')
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
