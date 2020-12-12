import typer

from controller import log
from controller.app import Application, Configuration
from controller.compose import Compose


@Application.app.command(help="Pull available images from docker hub")
def pull(
    include_all: bool = typer.Option(
        False,
        "--all",
        help="Include both core and custom images",
        show_default=False,
    ),
    quiet: bool = typer.Option(
        False,
        "--quiet",
        help="Pull without printing progress information",
        show_default=False,
    ),
) -> None:
    Application.get_controller().controller_init()

    if include_all:
        dc = Compose(files=Application.data.files)
        services_intersection = Application.data.services
    else:
        dc = Compose(files=Application.data.base_files)
        base_services_list = []
        for s in Application.data.base_services:
            base_services_list.append(s.get("name"))

        if Configuration.services_list:
            for s in Application.data.services:
                if s not in base_services_list:
                    Application.exit("Invalid service name: {}", s)
        # List of BASE active services (i.e. remove services not in base)
        services_intersection = list(
            set(Application.data.services).intersection(base_services_list)
        )

    options = {"SERVICE": services_intersection, "--quiet": quiet}
    dc.command("pull", options)

    if include_all:
        log.info("Images pulled from docker hub")
    else:
        log.info("Base images pulled from docker hub")
