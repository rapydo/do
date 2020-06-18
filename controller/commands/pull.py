from controller import log
from controller.compose import Compose


def __call__(services, base_services, base_files, **kwargs):

    dc = Compose(files=base_files)

    base_services_list = []
    for s in base_services:
        base_services_list.append(s.get("name"))

    for s in services:
        if s not in base_services_list:
            log.exit("Invalid service name: {}", s)
    # List of BASE active services (i.e. remove services not in base)
    services_intersection = list(set(services).intersection(base_services_list))

    options = {
        "SERVICE": services_intersection,
    }
    dc.command("pull", options)

    log.info("Base images pulled from docker hub")
