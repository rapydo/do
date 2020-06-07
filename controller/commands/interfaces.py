import os
import sys

from glom import glom

from controller import log
from controller.compose import Compose


def container_info(services_dict, service_name):
    return services_dict.get(service_name, None)


def container_service_exists(services_dict, service_name):
    return container_info(services_dict, service_name) is not None


def __call__(
    args,
    compose_config,
    files,
    hostname,
    production,
    conf_vars,
    services_dict,
    **kwargs
):

    db = args.get("service")
    if db == "list":
        print("List of available interfaces:")
        for s in compose_config:
            name = s.get("name", "")
            if name.endswith("ui"):
                print(" - {}".format(name[0:-2]))
        return True

    service = db + "ui"

    if not container_service_exists(services_dict, service):
        suggest = "You can use rapydo interfaces list to get available interfaces"
        log.exit("Container '{}' is not defined\n{}", service, suggest)

    port = args.get("port")
    publish = []

    info = container_info(services_dict, service)
    try:
        current_ports = info.get("ports", []).pop(0)
    except IndexError:
        log.exit("No default port found?")

    if port is None:
        port = current_ports.published
    else:
        try:
            int(port)
        except TypeError:
            log.exit("Port must be a valid integer")

        publish.append("{}:{}".format(port, current_ports.target))

    url = None
    if service == "swaggerui":
        BACKEND_PORT = glom(conf_vars, "env.BACKEND_PORT")
        if production:
            spec = "https://{}/api/specs".format(hostname)
        else:
            spec = "http://{}:{}/api/specs".format(hostname, BACKEND_PORT)
        url = "http://{}:{}?docExpansion=list&url={}".format(hostname, port, spec)

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

    dc = Compose(files=files)

    with suppress_stdout():
        # NOTE: this is suppressing also image build...
        detach = args.get("detach")
        dc.create_volatile_container(service, publish=publish, detach=detach)

    return True
