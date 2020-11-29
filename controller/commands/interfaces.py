from typing import Optional

import typer
from glom import glom

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

    url = None
    if service == "swaggerui":
        BACKEND_PORT = glom(Configuration.specs, "variables.env.BACKEND_PORT")
        swagger_host = f"{Configuration.hostname}:{port}"
        if Configuration.production:
            spec = f"https://{Configuration.hostname}/api/specs"
            url = f"https://{swagger_host}?docExpansion=list&url={spec}"
        else:
            spec = f"http://{Configuration.hostname}:{BACKEND_PORT}/api/specs"
            url = f"http://{swagger_host}?docExpansion=list&url={spec}"

    if url is not None:
        log.info("You can access {} web page here:\n\n{}\n", service, url)
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
