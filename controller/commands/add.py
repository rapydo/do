from controller import log


def create_endpoint():
    log.warning("Endpoint creation not implemented yet")


def create_task():
    log.warning("Task creation not implemented yet")


def create_component():
    log.warning("Component creation not implemented yet")


def create_service():
    log.warning("Service creation not implemented yet")


def __call__(args, **kwargs):

    functions = {
        "endpoint": create_endpoint,
        "task": create_task,
        "component": create_component,
        "service": create_service,
    }
    element = args.get("element")

    if element not in functions:
        log.exit(
            "Invalid element {}, please chose one of: {}",
            element,
            ", ".join(functions.keys()),
        )

    fn = functions.get(element)
    fn()
