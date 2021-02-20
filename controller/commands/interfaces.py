from typing import Optional

import typer

from controller import log
from controller.app import Application, Configuration
from controller.compose import Compose


@Application.app.command(help="Execute predefined interfaces to services")
def interfaces(
    service: str = typer.Argument(
        "list",
        help="Service name",
        show_default=False,
        autocompletion=Application.autocomplete_interfaces,
    ),
    detach: bool = typer.Option(
        False,
        "--detach",
        help="Detached mode to run the container in background",
        show_default=False,
    ),
    port: Optional[int] = typer.Option(
        None,
        "--port",
        "-p",
        help="port to be associated to the current service interface",
    ),
) -> bool:
    Application.get_controller().controller_init()

    if service == "list":
        print("List of available interfaces:")
        for service in Application.get_controller().get_available_interfaces():
            print(f" - {service}")
        return True

    service = service + "ui"

    if not container_service_exists(Application.data.services_dict, service):
        suggest = "You can use rapydo interfaces list to get available interfaces"
        Application.exit("Container '{}' is not defined\n{}", service, suggest)

    info = container_info(Application.data.services_dict, service)
    try:
        current_ports = info.get("ports", []).pop(0)
    except IndexError:  # pragma: no cover
        Application.exit("No default port found?")

    # cannot set current_ports.published as default in get
    # because since port is in args... but can be None
    if port is None:
        port = current_ports.published

    publish = [f"{port}:{current_ports.target}"]

    if service == "swaggerui":
        if Configuration.production:
            prot = "https"
        else:
            prot = "http"

        log.info(
            "You can access SwaggerUI web page here: {}\n",
            f"{prot}://{Configuration.hostname}:{port}",
        )
    else:
        log.info("Launching interface: {}", service)

    # from contextlib import contextmanager

    # @contextmanager
    # def suppress_stdout():
    #     """
    #     http://thesmithfam.org/blog/2012/10/25/
    #     temporarily-suppress-console-output-in-python/
    #     """
    #     with open(os.devnull, "w") as devnull:
    #         old_stdout = sys.stdout
    #         sys.stdout = devnull
    #         try:
    #             yield
    #         finally:
    #             sys.stdout = old_stdout

    dc = Compose(files=Application.data.files)

    # with suppress_stdout():
    #     # NOTE: this is suppressing also image build...
    dc.command("pull", {"SERVICE": [service]})

    dc.create_volatile_container(service, publish=publish, detach=detach)

    return True


def container_info(services_dict, service_name):
    return services_dict.get(service_name, None)


def container_service_exists(services_dict, service_name):
    return container_info(services_dict, service_name) is not None
