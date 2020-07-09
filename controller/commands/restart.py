from controller import log
from controller.compose import Compose


def __call__(services, files, **kwargs):

    options = {"SERVICE": services}

    dc = Compose(files=files)
    dc.command("restart", options)

    log.info("Stack restarted")
