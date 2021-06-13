from controller import log
from controller.app import Application


@Application.app.command(help="Stop running services, but do not remove them")
def stop() -> None:
    log.error("Stop command is not implemented in Swarm Mode")
    print("Stop is in contrast with the Docker Swarm approach")
    print("You can remove the stack => rapydo remove")
    print("Or you can scale all the services to zero => rapydo scale service=0")
