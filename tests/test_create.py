import os

from controller.templating import Templating
from tests import TemporaryRemovePath, exec_command


def test_failed_create(capfd):

    exec_command(
        capfd,
        "create first",
        "Missing option '--auth'",
    )

    exec_command(
        capfd,
        "create first --auth xyz",
        "Invalid value for '--auth'",
    )

    exec_command(
        capfd,
        "create first --auth postgres",
        "Missing option '--frontend'.",
    )

    exec_command(
        capfd,
        "create first --auth postgres --frontend xyz",
        "Invalid value for '--frontend'",
    )

    exec_command(
        capfd,
        "create first --auth postgres --frontend angular",
        "Current folder is not empty, cannot create a new project here.",
        "Found: ",
        "Use --current to force the creation here",
    )

    with open("data/logs/rapydo-controller.log") as f:
        logs = f.read().splitlines()
        assert logs[-1].endswith("Use --current to force the creation here")

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
        capfd,
        create_command,
        "Project first successfully created",
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

    # Delete a raw file in no-auto mode (i.e. manual creation)
    favicon = "projects/first/frontend/assets/favicon/favicon.ico"
    os.remove(favicon)
    exec_command(
        capfd,
        "create first --auth postgres --frontend angular --no-auto --current",
        f"File is missing: {favicon}",
    )
    # here a single and valid project is created (not initialized)
    exec_command(
        capfd,
        "create first --auth postgres --frontend angular --current",
        "Project folder already exists: projects/first/confs",
        f"Project file already exists: {pconf}",
        "Project first successfully created",
    )
