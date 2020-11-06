import typer

from controller import log
from controller.app import Application, Configuration
from controller.compose import Compose


@Application.app.command(help="Stop and remove containers")
def remove(
    rm_networks: bool = typer.Option(
        False,
        "--networks",
        "--net",
        help="Also remove containers networks",
        show_default=False,
    ),
    rm_all: bool = typer.Option(
        False,
        "--all",
        help="Also remove networks and persistent data stored in docker volumes",
        show_default=False,
    ),
) -> None:
    Application.get_controller().controller_init()

    dc = Compose(files=Application.data.files)

    if rm_networks or rm_all:

        if Configuration.services_list is not None:

            opt = "--networks" if rm_networks else "--all"

            Application.exit(
                "Incompatibile options {opt} and --service\n"
                + "rapydo remove {opt} is ALWAYS applied to EVERY container of the "
                + "stack due to the underlying docker-compose implementation. "
                + "If you want to continue remove --service option",
                opt=opt,
            )
        else:

            options = {
                "--volumes": rm_all,
                "--remove-orphans": False,
                "--rmi": "local",  # 'all'
            }
            dc.command("down", options)
    else:

        options = {
            "SERVICE": Application.data.services,
            # '--stop': True,  # BUG? not working
            "--force": True,
            "-v": False,  # dangerous?
        }
        dc.command("stop", options)
        dc.command("rm", options)

    log.info("Stack removed")
