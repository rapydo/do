import typer

from controller import log
from controller.app import Application, Configuration
from controller.deploy.swarm import Swarm


@Application.app.command(help="Stop and remove services")
def remove(
    rm_all: bool = typer.Option(
        False,
        "--all",
        help="Also remove networks and persistent data stored in docker volumes",
        show_default=False,
    ),
) -> None:
    Application.get_controller().controller_init()

    swarm = Swarm()

    if rm_all:
        log.warning("rm_all flag is not implemented yet")

    if rm_all:

        if Configuration.services_list is not None:

            Application.exit(
                "Incompatibile options --all and --service\n"
                + "rapydo remove --all is ALWAYS applied to EVERY container of the "
                + "stack due to the underlying implementation. "
                + "If you want to continue remove --service option"
            )
        else:

            # options = {
            #     "--volumes": rm_all,
            #     "--remove-orphans": False,
            #     "--rmi": "local",  # 'all'
            # }
            # dc.command("down", options)
            log.warning("Not implemented")
    else:

        # options = {
        #     "SERVICE": Application.data.services,
        #     # '--stop': True,  # BUG? not working
        #     "--force": True,
        #     "-v": False,  # dangerous?
        # }
        # dc.command("stop", options)
        # dc.command("rm", options)

        swarm.remove()

    log.info("Stack removed")
