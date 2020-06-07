from controller import log
from controller.compose import Compose


def __call__(args, files, services, **kwargs):

    dc = Compose(files=files)
    if args.get("no_detach", False):
        detach = False
    else:
        detach = True

    dc.start_containers(services, detach=detach)

    log.info("Stack started")
