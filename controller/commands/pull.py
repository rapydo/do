from controller import log
from controller.app import Application, Configuration
from controller.compose import Compose


@Application.app.command(help="Pull available images from docker hub")
def pull():
    Application.controller.controller_init()

    dc = Compose(files=Application.data.base_files)

    base_services_list = []
    for s in Application.data.base_services:
        base_services_list.append(s.get("name"))

    if Configuration.services_list:
        for s in Application.data.services:
            if s not in base_services_list:
                log.exit("Invalid service name: {}", s)
    # List of BASE active services (i.e. remove services not in base)
    services_intersection = list(
        set(Application.data.services).intersection(base_services_list)
    )

    options = {
        "SERVICE": services_intersection,
    }
    dc.command("pull", options)

    log.info("Base images pulled from docker hub")
