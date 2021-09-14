import re
from datetime import date, datetime, timedelta
from enum import Enum
from typing import Dict, List

import typer
from zxcvbn import zxcvbn

from controller import GREEN, PROJECTRC, RED, SWARM_MODE, log, print_and_exit
from controller.app import Application, Configuration
from controller.deploy.compose_v2 import Compose
from controller.deploy.swarm import Swarm
from controller.templating import Templating
from controller.templating import password as generate_random_password

# make this configurable
PASSWORD_EXPIRATION = 90

UPDATE_LABEL = "updated by rapydo password on"


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
def parse_projectrc() -> Dict[str, datetime]:

    updates: Dict[str, datetime] = {}
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

            if UPDATE_LABEL in line:
                variable = line.split(":")[0]
                m = re.search(
                    # This is is expected to be a date yyyy-mm-dd
                    # this reg exp will start to fail starting from 1st Jan 2100 :-D
                    fr".*{UPDATE_LABEL} (20[0-9][0-9]-[0-1][0-9]-[0-3][0-9])$",
                    line,
                )

                if m:
                    updates[variable] = datetime.strptime(m.group(1), "%Y-%m-%d")

    return updates


# Note: can't directly use utilities in app.py because in this case we want to
# maintain all values (not only templated variables) and we also want to keep comments
def update_projectrc(variables: Dict[str, str]) -> None:

    today = date.today().strftime("%Y-%m-%d")
    with open(PROJECTRC) as f:
        lines = f.readlines()
        for index, line in enumerate(lines):

            for variable, value in variables.items():
                if line.strip().startswith(variable):
                    blanks = line.index(variable)
                    pref = " " * blanks
                    annotation = f"# {UPDATE_LABEL} {today}"
                    lines[index] = f'{pref}{variable}: "{value}"  {annotation}\n'

    templating = Templating()
    templating.make_backup(PROJECTRC)
    with open(PROJECTRC, "w") as f:
        for line in lines:
            f.write(line)


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

    # No service specified, only a summary will be reported
    if not service:

        last_updates = parse_projectrc()
        now = datetime.now()

        h1 = "SERVICE"
        h2 = "VARIABLE"
        h3 = "SCORE"
        h4 = "LAST CHANGE"
        # note three blanks to center the score
        print(f"{h1:12}{h2:22}{h3:5}  {h4}")
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

                if v in last_updates:
                    last_change = last_updates.get(v, datetime.fromtimestamp(0))
                    expiration_date = last_change + timedelta(days=PASSWORD_EXPIRATION)
                    expired = now > expiration_date
                    last_change_text = last_change.strftime("%Y-%m-%d")
                else:
                    expired = True
                    last_change_text = "N/A"

                # note two blanks to center the score
                line = f"{s.value:12}{v:22}  {score:5}{last_change_text}"
                if expired:
                    print(RED(line))
                else:
                    print(GREEN(line))

    # In this case a service is asked to be updated
    else:

        compose = Compose(Application.data.files)
        if SWARM_MODE:
            swarm = Swarm()
            running_services = swarm.get_running_services(Configuration.project)
        else:
            running_services = compose.get_running_services(Configuration.project)

        if not new_password:
            new_password = get_random_password()
        # log.critical(new_password)

        variables = get_service_passwords(service)
        new_variables = {variable: new_password for variable in variables}

        # Some services can only be updated if already running,
        # others can be updated even if offline,
        # but in every case if the stack is running it has to be restarted
        is_running = service.value in running_services
        is_running_needed = False

        if service == Services.redis:
            is_running_needed = False
        else:
            print_and_exit("Change password for {} not implemented yet", service.value)

        if is_running_needed and not is_running:
            print_and_exit(
                "Can't update {} since it is not running. Please start your stack",
                service.value,
            )

        update_projectrc(new_variables)

        # here specific operation have to be implemented.
        # - Nothing for Redis, projectrc update is enough

        if is_running:

            if SWARM_MODE:

                compose.dump_config(Application.data.services)
                swarm.deploy()

            else:
                compose.start_containers(Application.data.services)

        log.info(
            "The password of {} has been changed. "
            "Please find the new password into your .projectrc file as {} variable",
            service.value,
            variables[0],
        )
