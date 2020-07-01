from controller import log


def __call__(args, **kwargs):
    service = args.get("service")

    log.warning("Backup on {} is not implemented", service)
