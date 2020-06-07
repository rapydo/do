from controller import log
from controller.compose import Compose
from controller.project import ANGULAR


def __call__(args, files, frontend, **kwargs):

    dc = Compose(files=files)
    service = args.get("service")
    no_tty = args.get("no_tty")
    default_command = args.get("default_command")

    user = args.get("user")
    if user is not None and user.strip() == "":
        developer_services = ["backend", "celery", "celeryui", "celery-beat"]

        if service in developer_services:
            user = "developer"
        elif service in ["frontend"]:
            if frontend == ANGULAR:
                user = "node"
        elif service == "postgres":
            user = "postgres"
        # Tests are not based on neo4j... pull an additional image and slow down the
        # test suite only to test this case is not needed, we can assume it works
        # having tested 3 images out of 4
        elif service == "neo4j":  # pragma: no cover
            user = "neo4j"
        else:
            # None == get the docker-compose default
            user = None
    log.verbose("Command as user '{}'", user)

    command = args.get("command")
    # Not easy to test all default commands...
    if command is None:  # pragma: no cover
        if not default_command:
            command = "bash"
        elif service == "backend":
            command = "restapi launch"
        elif service == "neo4j":
            command = "bin/cypher-shell"
        else:
            command = "bash"

    return dc.exec_command(service, user=user, command=command, disable_tty=no_tty)
