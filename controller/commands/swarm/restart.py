from controller import RED, log, print_and_exit
from controller.app import Application, Configuration
from controller.deploy.compose_v2 import Compose as ComposeV2
from controller.deploy.swarm import Swarm


@Application.app.command(help="Update deployed services")
def restart() -> None:

    swarm = Swarm()

    if not swarm.stack_is_running(Configuration.project):
        print_and_exit(
            "Stack {} is not running, deploy it with {command}",
            Configuration.project,
            command=RED("rapydo start"),
        )

    # len of projectname and underscore
    plen = 1 + len(Configuration.project)
    # To be replaced with removeprefix
    services = [x.spec.name[plen:] for x in swarm.docker.service.list()]

    Application.get_controller().controller_init(services)

    log.info("Restarting services:")

    compose = ComposeV2(Application.data.files)
    compose.dump_config(Application.data.services)
    swarm.deploy()

    log.info("Stack restarted")
