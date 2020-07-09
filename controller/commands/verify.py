from controller import log
from controller.compose import Compose


def __call__(args, files, **kwargs):
    """ Verify one service connection (inside backend) """
    service = args.get("service")
    dc = Compose(files=files)
    command = "restapi verify --services {}".format(service)

    try:
        return dc.exec_command("backend", command=command)
    except SystemExit as e:
        log.critical(e)
