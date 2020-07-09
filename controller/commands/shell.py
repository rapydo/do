from controller import log
from controller.compose import Compose
from controller.utilities import services


def __call__(args, files, frontend, **kwargs):

    dc = Compose(files=files)
    service = args.get("service")
    no_tty = args.get("no_tty")
    detach = args.get("detach")
    default_command = args.get("default_command")

    user = args.get("user")
    if user is not None and user.strip() == "":
        user = services.get_default_user(service, frontend)

    log.verbose("Command as user '{}'", user)

    command = args.get("command")
    if command:
        log.debug("Requested command: {}", command)
    elif default_command:
        command = services.get_default_command(service)
    else:
        command = "bash"

    return dc.exec_command(
        service, user=user, command=command, disable_tty=no_tty, detach=detach
    )
