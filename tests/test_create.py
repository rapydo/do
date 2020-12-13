"""
This module will test all the combinations of the create command.
Other tests that will create projects will assume the command fully working
and will only use the specific configuration needed by the test itself
"""

import os

from controller.templating import Templating
from tests import TemporaryRemovePath, exec_command


def test_create(capfd):

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

    # Test extended projects

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

    # Test Services Activation

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

    # Test Celery Activation

    opt = "--frontend no --current --force --auth neo4j"
    project_configuration = "projects/testcelery/project_configuration.yaml"

    def verify_celery_configuration(services_list, broker, backend):

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

    verify_celery_configuration([], "RABBIT", "RABBIT")
    verify_celery_configuration(["rabbit"], "RABBIT", "RABBIT")
    verify_celery_configuration(["redis"], "REDIS", "REDIS")
    verify_celery_configuration(["mongo"], "RABBIT", "MONGODB")
    verify_celery_configuration(["rabbit", "redis"], "RABBIT", "REDIS")
    verify_celery_configuration(["rabbit", "mongo"], "RABBIT", "MONGODB")
    verify_celery_configuration(["redis", "mongo"], "REDIS", "REDIS")
    verify_celery_configuration(["rabbit", "redis", "mongo"], "RABBIT", "REDIS")
