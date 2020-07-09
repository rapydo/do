import os
import sys

import typer
from glom import glom

from controller import log
from controller.app import Application
from controller.compose import Compose


@Application.app.command(help="Execute predefined interfaces to services")
def interfaces(
    service: str = typer.Argument("list", help="Service name", show_default=False),
    detach: bool = typer.Option(
        False,
        "--detach",
        help="Detached mode to run the container in background",
        show_default=False,
    ),
    port: int = typer.Option(
        None,
        "--port",
        "-p",
        help="port to be associated to the current service interface",
    ),
):

    if service == "list":
        print("List of available interfaces:")
        for s in Application.data.compose_config:
            name = s.get("name", "")
            if name.endswith("ui"):
                print(" - {}".format(name[0:-2]))
        return True

    service = service + "ui"

    if not container_service_exists(Application.data.services_dict, service):
        suggest = "You can use rapydo interfaces list to get available interfaces"
        log.exit("Container '{}' is not defined\n{}", service, suggest)

    info = container_info(Application.data.services_dict, service)
    try:
        current_ports = info.get("ports", []).pop(0)
    except IndexError:  # pragma: no cover
        log.exit("No default port found?")

    # cannot set current_ports.published as default in get
    # because since port is in args... but can be None
    if port is None:
        port = str(current_ports.published)

    if not port.isnumeric():
        log.exit("Port must be a valid integer")

    publish = [f"{port}:{current_ports.target}"]

    url = None
    if service == "swaggerui":
        BACKEND_PORT = glom(Application.data.conf_vars, "env.BACKEND_PORT")
        if Application.data.production:
            spec = f"https://{Application.data.hostname}/api/specs"
        else:
            spec = f"http://{Application.data.hostname}:{BACKEND_PORT}/api/specs"
        url = f"http://{Application.data.hostname}:{port}?docExpansion=list&url={spec}"

    if url is not None:
        log.info("You can access {} web page here:\n\n{}\n", service, url)
    else:
        log.info("Launching interface: {}", service)

    from contextlib import contextmanager

    @contextmanager
    def suppress_stdout():
        """
        http://thesmithfam.org/blog/2012/10/25/
        temporarily-suppress-console-output-in-python/
        """
        with open(os.devnull, "w") as devnull:
            old_stdout = sys.stdout
            sys.stdout = devnull
            try:
                yield
            finally:
                sys.stdout = old_stdout

    dc = Compose(files=Application.data.files)

    with suppress_stdout():
        # NOTE: this is suppressing also image build...
        dc.create_volatile_container(service, publish=publish, detach=detach)

    return True


def container_info(services_dict, service_name):
    return services_dict.get(service_name, None)


def container_service_exists(services_dict, service_name):
    return container_info(services_dict, service_name) is not None
