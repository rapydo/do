from datetime import datetime
from enum import Enum
from typing import List, Set, Union

import typer
from zxcvbn import zxcvbn

from controller import PROJECTRC, SWARM_MODE, log, print_and_exit
from controller.app import Application, Configuration
from controller.deploy.compose_v2 import Compose
from controller.deploy.swarm import Swarm
from controller.templating import password as generate_random_password


class Services(str, Enum):
    backend = "backend"
    neo4j = "neo4j"
    postgres = "postgres"
    mariadb = "mariadb"
    mongodb = "mongodb"
    rabbit = "rabbit"
    redis = "redis"
    registry = "registry"
    flower = "flower"


def get_service_passwords(service: Services) -> List[str]:

    if service == Services.backend:
        return ["AUTH_DEFAULT_PASSWORD"]
    if service == Services.neo4j:
        return ["NEO4J_PASSWORD"]
    if service == Services.postgres:
        return ["ALCHEMY_PASSWORD"]
    if service == Services.mariadb:
        return ["ALCHEMY_PASSWORD", "MYSQL_ROOT_PASSWORD"]
    if service == Services.mongodb:
        return ["MONGO_PASSWORD"]
    if service == Services.rabbit:
        return ["RABBITMQ_PASSWORD"]
    if service == Services.redis:
        return ["REDIS_PASSWORD"]
    if service == Services.registry:
        return ["REGISTRY_PASSWORD"]
    if service == Services.flower:
        return ["FLOWER_PASSWORD"]
    return []  # pragma: no cover


# Note: can't directly extract yaml with comments because it is not supported
# https://github.com/yaml/pyyaml/issues/90
def parse_projectrc() -> None:
    with open(PROJECTRC) as f:
        lines = f.readlines()

        env_seen = False
        for line in lines:
            line = line.strip()

            # Skip empty lines
            if not line:
                continue

            # Skip everything before the env block
            if line == "env:":
                env_seen = True
                continue
            elif not env_seen:
                continue
            log.critical(line)


def get_random_password() -> str:

    password = generate_random_password(
        length=16, param_not_used="", symbols="%*,-.=?[]^_~"
    )

    result = zxcvbn(password)
    score = result["score"]
    # Should never happens since 16 characters with symbols is very unlikely to be weak
    if score < 4:  # pragma: no cover
        log.warning("Generated password is not strong enough, resampling again")
        return get_random_password()
    return password


def change_backend_password(new_password: str, running_services: Set[str]) -> None:
    service = "backend"
    log.critical("Change password for {} not implemented yet", service)


def change_neo4j_password(new_password: str, running_services: Set[str]) -> None:
    service = "neo4j"
    log.critical("Change password for {} not implemented yet", service)


def change_postgres_password(new_password: str, running_services: Set[str]) -> None:
    service = "postgres"
    log.critical("Change password for {} not implemented yet", service)


def change_mariadb_password(new_password: str, running_services: Set[str]) -> None:
    service = "mariadb"
    log.critical("Change password for {} not implemented yet", service)


def change_mongodb_password(new_password: str, running_services: Set[str]) -> None:
    service = "mongodb"
    log.critical("Change password for {} not implemented yet", service)


def change_rabbit_password(new_password: str, running_services: Set[str]) -> None:
    service = "rabbit"
    log.critical("Change password for {} not implemented yet", service)


def change_redis_password(new_password: str, running_services: Set[str]) -> None:
    service = "redis"
    log.critical("Change password for {} not implemented yet", service)


def change_registry_password(new_password: str, running_services: Set[str]) -> None:
    service = "registry"
    log.critical("Change password for {} not implemented yet", service)


def change_flower_password(new_password: str, running_services: Set[str]) -> None:
    service = "flower"
    log.critical("Change password for {} not implemented yet", service)


@Application.app.command(help="Manage services passwords")
def password(
    service: Services = typer.Argument(None, help="Service name"),
    new_password: str = typer.Option(
        None,
        "--password",
        help="Force the given password instead of create a random password",
        show_default=False,
    ),
) -> None:

    Application.get_controller().controller_init()

    if not service:

        parse_projectrc()

        h1 = "SERVICE"
        h2 = "VARIABLE"
        h3 = "SCORE"
        h4 = "LAST CHANGE"
        # note two blanks to center the score
        print(f"{h1:12}{h2:22}{h3:6}  {h4}")
        for s in Services:
            # This should never happens and can't be (easily) tested
            if s.value not in Application.data.base_services:  # pragma: no cover
                print_and_exit("Command misconfiguration, unknown {} service", s.value)
            if s.value not in Application.data.active_services:
                continue

            variables = get_service_passwords(s)

            for v in variables:

                password = Application.env.get(v)
                result = zxcvbn(password)
                score = str(result["score"])
                last_change = datetime.fromtimestamp(0)

                # note two blanks to center the score
                print(f"{s.value:12}{v:22}  {score:6}{last_change}")
    else:

        engine: Union[Swarm, Compose] = (
            Swarm() if SWARM_MODE else Compose(Application.data.files)
        )

        running_services = engine.get_running_services(Configuration.project)
        if not new_password:
            new_password = get_random_password()
        # log.critical(new_password)

        log.critical("running services: {}", running_services)

        if service == Services.backend:
            change_backend_password(new_password, running_services)
        elif service == Services.neo4j:
            change_neo4j_password(new_password, running_services)
        elif service == Services.postgres:
            change_postgres_password(new_password, running_services)
        elif service == Services.mariadb:
            change_mariadb_password(new_password, running_services)
        elif service == Services.mongodb:
            change_mongodb_password(new_password, running_services)
        elif service == Services.rabbit:
            change_rabbit_password(new_password, running_services)
        elif service == Services.redis:
            change_redis_password(new_password, running_services)
        elif service == Services.registry:
            change_registry_password(new_password, running_services)
        elif service == Services.flower:
            change_flower_password(new_password, running_services)
