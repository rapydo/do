from glom import glom

from controller import log


def walk_services(actives, dependecies, index=0):

    if index >= len(actives):
        return actives

    next_active = actives[index]

    for service in dependecies.get(next_active, []):
        if service not in actives:
            actives.append(service)

    index += 1

    return walk_services(actives, dependecies, index)


def find_active(services):
    """
    Check only services involved in current mode,
    which is equal to services 'activated' + 'depends_on'.
    """

    dependencies = {}
    all_services = {}
    base_actives = []

    for service in services:

        name = service.get("name")
        all_services[name] = service
        dependencies[name] = list(service.get("depends_on", {}).keys())

        ACTIVATE = glom(service, "environment.ACTIVATE", default=0)
        is_active = str(ACTIVATE) == "1"
        if is_active:
            base_actives.append(name)

    log.verbose("Base active services = {}", base_actives)
    log.verbose("Services dependencies = {}", dependencies)
    active_services = walk_services(base_actives, dependencies)
    return all_services, active_services


def apply_variables(dictionary, variables):

    new_dict = {}
    for key, value in dictionary.items():
        if isinstance(value, str) and value.startswith("$$"):
            value = variables.get(value.lstrip("$"), None)
        else:
            pass
        new_dict[key] = value

    return new_dict


vars_to_services_mapping = {
    "CELERYUI_USER": ["celeryui"],
    "CELERYUI_PASSWORD": ["celeryui"],
    "RABBITMQ_USER": ["rabbit"],
    "RABBITMQ_PASSWORD": ["rabbit"],
    "ALCHEMY_USER": ["postgres", "mariadb"],
    "ALCHEMY_PASSWORD": ["postgres", "mariadb"],
    "NEO4J_PASSWORD": ["neo4j"],
    "IRODS_ANONYMOUS": ["icat"],
    "AUTH_DEFAULT_PASSWORD": ["backend"],
    "AUTH_DEFAULT_USERNAME": ["backend"],
    "SMTP_PORT": ["backend"],
    "SMTP_ADMIN": ["backend"],
    "SMTP_NOREPLY": ["backend"],
    "SMTP_HOST": ["backend"],
    "SMTP_USERNAME": ["backend"],
    "SMTP_PASSWORD": ["backend"],
    "IRODS_PASSWORD": ["icat"],
    "IRODS_USER": ["icat"],
}


def normalize_placeholder_variable(key):
    if key == "NEO4J_AUTH":
        return "NEO4J_PASSWORD"

    if key == "POSTGRES_USER":
        return "ALCHEMY_USER"
    if key == "POSTGRES_PASSWORD":
        return "ALCHEMY_PASSWORD"

    if key == "MYSQL_USER":
        return "ALCHEMY_USER"
    if key == "MYSQL_PASSWORD":
        return "ALCHEMY_PASSWORD"

    if key == "RABBITMQ_DEFAULT_USER":
        return "RABBITMQ_USER"
    if key == "RABBITMQ_DEFAULT_PASS":
        return "RABBITMQ_PASSWORD"

    return key
