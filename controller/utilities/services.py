import sys
from collections import OrderedDict
from typing import Any, Dict, List, Optional, Tuple

from glom import glom

from controller import log
from controller.project import ANGULAR


def get_services(services: Optional[str], default: List[str]) -> List[str]:

    if services:
        return services.split(",")
    return default


def walk_services(
    actives: List[str], dependecies: Dict[str, List[str]], index: int = 0
) -> List[str]:

    if index >= len(actives):
        return actives

    next_active = actives[index]

    for service in dependecies.get(next_active, []):
        # Not easy to test, since we have few services with dependencies
        if service not in actives:  # pragma: no cover
            actives.append(service)

    index += 1

    return walk_services(actives, dependecies, index)


def find_active(services: List[Any]) -> Tuple[Dict[str, List[Any]], List[str]]:
    """
    Check only services involved in current mode,
    which is equal to services 'activated' + 'depends_on'.
    """

    dependencies: Dict[str, List[str]] = {}
    all_services: Dict[str, List[Any]] = {}
    base_actives: List[str] = []

    for service in services:

        name = service.get("name")
        all_services[name] = service
        dependencies[name] = list(service.get("depends_on", {}).keys())

        ACTIVATE = glom(service, "environment.ACTIVATE", default=0)
        is_active = str(ACTIVATE) == "1"
        if is_active:
            base_actives.append(name)

    log.debug("Base active services = {}", base_actives)
    log.debug("Services dependencies = {}", dependencies)
    active_services = walk_services(base_actives, dependencies)
    return all_services, active_services


def apply_variables(
    dictionary: "OrderedDict[str, Any]", variables: Dict[str, Any]
) -> Dict[str, Any]:

    new_dict: Dict[str, Any] = {}
    for key, value in dictionary.items():
        if isinstance(value, str) and value.startswith("$$"):
            value = variables.get(value.lstrip("$"), None)
        else:
            pass
        new_dict[key] = value

    return new_dict


vars_to_services_mapping: Dict[str, List[str]] = {
    "CELERYUI_USER": ["celeryui"],
    "CELERYUI_PASSWORD": ["celeryui"],
    "RABBITMQ_USER": ["rabbit"],
    "RABBITMQ_PASSWORD": ["rabbit"],
    "ALCHEMY_USER": ["postgres", "mariadb"],
    "ALCHEMY_PASSWORD": ["postgres", "mariadb"],
    "NEO4J_PASSWORD": ["neo4j"],
    "NEO4J_HEAP_SIZE": ["neo4j"],
    "NEO4J_PAGECACHE_SIZE": ["neo4j"],
    "AUTH_DEFAULT_PASSWORD": ["backend"],
    "AUTH_DEFAULT_USERNAME": ["backend"],
    "SMTP_PORT": ["backend"],
    "SMTP_ADMIN": ["backend"],
    "SMTP_NOREPLY": ["backend"],
    "SMTP_HOST": ["backend"],
    "SMTP_USERNAME": ["backend"],
    "SMTP_PASSWORD": ["backend"],
    "TELEGRAM_API_KEY": ["bot"],
    "TELEGRAM_ADMINS": ["bot"],
}


def normalize_placeholder_variable(key: str) -> str:
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

    if key == "NEO4J_dbms_memory_heap_max__size":
        return "NEO4J_HEAP_SIZE"
    if key == "NEO4J_dbms_memory_heap_initial__size":
        return "NEO4J_HEAP_SIZE"

    if key == "NEO4J_dbms_memory_pagecache_size":
        return "NEO4J_PAGECACHE_SIZE"

    if key == "CYPRESS_AUTH_DEFAULT_USERNAME":
        return "AUTH_DEFAULT_USERNAME"
    if key == "CYPRESS_AUTH_DEFAULT_PASSWORD":
        return "AUTH_DEFAULT_PASSWORD"

    return key


def get_celerybeat_scheduler(env: Dict[str, str]) -> str:

    if env.get("ACTIVATE_CELERYBEAT", "0") == "0":
        return "Unknown"

    celery_backend = env.get("CELERY_BACKEND")

    if celery_backend is None:
        return "Unknown"

    if celery_backend == "MONGODB":
        return "celerybeatmongo.schedulers.MongoScheduler"

    if celery_backend == "REDIS":
        return "redbeat.RedBeatScheduler"

    return "Unknown"


def check_rabbit_password(pwd: str) -> None:
    invalid_rabbit_characters = ["£", "§", "”", "’"]
    if any([c in pwd for c in invalid_rabbit_characters]):
        log.critical("Not allowed characters found in RABBITMQ_PASSWORD.")
        log.critical(
            "Some special characters, including {}, are not allowed "
            "because make RabbitMQ crash at startup",
            " ".join(invalid_rabbit_characters),
        )
        sys.exit(1)


def get_default_user(service: str, frontend: Optional[str]) -> Optional[str]:

    if service in ["backend", "celery", "celeryui", "celery-beat"]:
        return "developer"

    if service in ["frontend"]:
        if frontend == ANGULAR:
            return "node"

    if service == "postgres":
        return "postgres"

    if service == "neo4j":
        return "neo4j"

    return None


def get_default_command(service: str) -> str:

    if service == "backend":
        return "restapi launch"

    if service == "bot":
        return "restapi bot"

    if service == "neo4j":
        return "bin/cypher-shell"

    if service == "postgres":
        return "psql"

    return "bash"
