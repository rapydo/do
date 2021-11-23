import warnings
from typing import Dict, Iterable, List, Optional, Union

from controller import ComposeServices, EnvType, log, print_and_exit
from controller.project import ANGULAR


def get_services(
    services: Optional[Union[str, Iterable[str]]],
    default: List[str],
) -> List[str]:

    return_list: List[str] = []
    if not services:
        return_list = sorted(default)
    elif isinstance(services, str):
        warnings.warn("Deprecated use of -s option")
        return_list = sorted(services.split(","))
    else:
        return_list = sorted(services)

    excluded_services_list: List[str] = [
        s[1:] for s in return_list if s.startswith("_")
    ]

    if excluded_services_list:

        # Filter out _ services from return_list
        return_list = [s for s in return_list if not s.startswith("_")]

        for service in excluded_services_list:
            if service not in return_list:
                print_and_exit("No such service: {}", service)

        return sorted(s for s in return_list if s not in excluded_services_list)

    return return_list


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


def find_active(services: ComposeServices) -> List[str]:
    """
    Check only services involved in current mode,
    which is equal to services 'activated' + 'depends_on'.
    """

    dependencies: Dict[str, List[str]] = {}
    base_actives: List[str] = []

    for name, service in services.items():

        dependencies[name] = list(service.depends_on.keys())

        if service.environment and service.environment.get("ACTIVATE", "0") == "1":
            base_actives.append(name)

    log.debug("Base active services = {}", base_actives)
    # log.debug("Services dependencies = {}", dependencies)
    active_services = walk_services(base_actives, dependencies)
    return active_services


vars_to_services_mapping: Dict[str, List[str]] = {
    "FLOWER_USER": ["flower"],
    "FLOWER_PASSWORD": ["flower"],
    "RABBITMQ_USER": ["rabbit"],
    "RABBITMQ_PASSWORD": ["rabbit"],
    "REDIS_PASSWORD": ["redis"],
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
    "MONGO_PASSWORD": ["mongodb"],
    "MONGO_USER": ["mongodb"],
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

    if key == "DEFAULT_USER":
        return "RABBITMQ_USER"
    if key == "DEFAULT_PASS":
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

    if key == "MONGO_INITDB_ROOT_PASSWORD":
        return "MONGO_PASSWORD"
    if key == "MONGO_INITDB_ROOT_USERNAME":
        return "MONGO_USER"

    return key


def get_celerybeat_scheduler(env: Dict[str, EnvType]) -> str:

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


def check_rabbit_password(pwd: Optional[EnvType]) -> None:
    if pwd:
        invalid_characters = ["£", "§", "”", "’"]
        if any(c in str(pwd) for c in invalid_characters):
            log.critical("Not allowed characters found in RABBITMQ_PASSWORD.")
            print_and_exit(
                "Some special characters, including {}, are not allowed "
                "because make RabbitMQ crash at startup",
                " ".join(invalid_characters),
            )


def check_redis_password(pwd: Optional[EnvType]) -> None:
    if pwd:
        invalid_characters = ["#"]
        if any(c in str(pwd) for c in invalid_characters):
            log.critical("Not allowed characters found in REDIS_PASSWORD.")
            print_and_exit(
                "Some special characters, including {}, are not allowed "
                "because make some clients to fail to connect",
                " ".join(invalid_characters),
            )


def check_mongodb_password(pwd: Optional[EnvType]) -> None:
    if pwd:
        invalid_characters = ["#"]
        if any(c in str(pwd) for c in invalid_characters):
            log.critical("Not allowed characters found in MONGO_PASSWORD.")
            print_and_exit(
                "Some special characters, including {}, are not allowed "
                "because make some clients to fail to connect",
                " ".join(invalid_characters),
            )


def get_default_user(service: str) -> Optional[str]:

    if service in ["backend", "celery", "flower", "celerybeat"]:
        return "developer"

    if service in ["frontend"]:
        from controller.app import Configuration

        if Configuration.frontend == ANGULAR:
            return "node"

    if service == "postgres":
        return "postgres"

    if service == "neo4j":
        return "neo4j"

    if service == "rabbit":
        return "rabbitmq"

    return None


def get_default_command(service: str) -> str:

    if service == "backend":
        return "restapi launch"

    if service == "bot":
        return "restapi bot"

    if service == "neo4j":
        return "bin/cypher-shell"

    if service == "postgres":
        return 'sh -c \'psql -U "$POSTGRES_USER" "$POSTGRES_DEFAULT_DB"\''

    if service == "mariadb":
        return 'sh -c \'mysql -D"$MYSQL_DATABASE" -u"$MYSQL_USER" -p"$MYSQL_PASSWORD"\''

    if service == "registry":
        return "ash"

    return "bash"
