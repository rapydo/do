from controller import log
from controller.compose import Compose


def __call__(args, services, files, **kwargs):

    # if provided at command line, use specific service instead of general services opt
    if args.get("service") is not None:
        services = [args.get("service")]

    options = {
        "--follow": args.get("follow", False),
        "--tail": args.get("tail", "100"),
        "--no-color": False,
        "--timestamps": True,
        "SERVICE": services,
    }

    dc = Compose(files=files)
    try:
        dc.command("logs", options)
    except KeyboardInterrupt:
        log.info("Stopped by keyboard")
