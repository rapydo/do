import re
from datetime import date, datetime, timedelta
from enum import Enum
from typing import Dict, List

import typer
from tabulate import tabulate
from zxcvbn import zxcvbn

from controller import (
    GREEN,
    PROJECTRC,
    RED,
    REGISTRY,
    SWARM_MODE,
    TABLE_FORMAT,
    log,
    print_and_exit,
)
from controller.app import Application, Configuration
from controller.deploy.compose import Compose as ComposeV1
from controller.deploy.compose_v2 import Compose
from controller.deploy.docker import Docker
from controller.deploy.swarm import Swarm
from controller.templating import Templating
from controller.templating import password as generate_random_password

# make this configurable
PASSWORD_EXPIRATION = 90

UPDATE_LABEL = "updated on"


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
    annotation = f"# {UPDATE_LABEL} {today}"
    with open(PROJECTRC) as f:
        lines = f.readlines()
        append_additional_lines: List[str] = []

        pref = ""
        for line in lines:
            if line.strip().startswith("env:"):
                blanks = line.index("env:")
                # Add 1 indentation level
                blanks = int(3 * blanks / 2)
                pref = " " * blanks

        if not pref:  # pragma: no cover
            print_and_exit("Malformed .projectrc file, can't find an env block")

        for variable, value in variables.items():
            for index, line in enumerate(lines):
                # If the variable is found in .projectrc, let's update it
                if line.strip().startswith(variable):
                    lines[index] = f'{pref}{variable}: "{value}"  {annotation}\n'
                    break
            # if the variable is not found in .projectrc, let's append as additional
            else:
                append_additional_lines.append(
                    f'{pref}{variable}: "{value}"  {annotation}\n'
                )

    templating = Templating()
    templating.make_backup(PROJECTRC)
    with open(PROJECTRC, "w") as f:
        last_line = ""
        for line in lines + append_additional_lines:
            last_line = line
            f.write(line)
            if not line.endswith("\n"):
                f.write("\n")

        # If last line is not an empty line, let's add a newline at the end of file
        if last_line.strip():
            f.write("\n")

    # Write again the .env file
    Application.get_controller().load_projectrc()
    Application.get_controller().read_specs(read_extended=True)
    Application.get_controller().make_env()


def get_random_password() -> str:

    password = generate_random_password(
        length=16, param_not_used="", symbols="%*,-.=^_~"
    )

    result = zxcvbn(password)
    score = result["score"]
    # Should never happens since 16 characters with symbols is very unlikely to be weak
    if score < 4:  # pragma: no cover
        log.warning("Generated password is not strong enough, sampling again")
        return get_random_password()
    return password


@Application.app.command(help="Manage services passwords")
def password(
    service: Services = typer.Argument(None, help="Service name"),
    random: bool = typer.Option(
        False,
        "--random",
        help="Generate a random password",
        show_default=False,
    ),
    new_password: str = typer.Option(
        None,
        "--password",
        help="Force the given password",
        show_default=False,
    ),
) -> None:

    Application.get_controller().controller_init()

    # No service specified, only a summary will be reported
    if not service:

        if random:
            print_and_exit("--random flag is not supported without a service")

        if new_password:
            print_and_exit("--password option is not supported without a service")

        MIN_PASSWORD_SCORE = int(
            Application.env.get("MIN_PASSWORD_SCORE", 2)  # type: ignore
        )

        last_updates = parse_projectrc()
        now = datetime.now()

        table: List[List[str]] = []
        for s in Services:
            # This should never happens and can't be (easily) tested
            if s.value not in Application.data.base_services:  # pragma: no cover
                print_and_exit("Command misconfiguration, unknown {} service", s.value)
            if (
                s != Services.registry
                and s.value not in Application.data.active_services
            ):
                continue

            variables = get_service_passwords(s)

            for variable in variables:

                password = Application.env.get(variable)
                result = zxcvbn(password)
                score = result["score"]

                if variable in last_updates:
                    change_date = last_updates.get(variable, datetime.fromtimestamp(0))
                    expiration_date = change_date + timedelta(days=PASSWORD_EXPIRATION)
                    expired = now > expiration_date
                    last_change = change_date.strftime("%Y-%m-%d")
                else:
                    expired = True
                    last_change = "N/A"

                pass_line: List[str] = []

                pass_line.append(s.value)
                pass_line.append(variable)

                if expired:
                    pass_line.append(RED(last_change))
                else:
                    pass_line.append(GREEN(last_change))

                if score < MIN_PASSWORD_SCORE:
                    pass_line.append(RED(score))
                else:
                    pass_line.append(GREEN(score))

                table.append(pass_line)

        print("")
        print(
            tabulate(
                table,
                tablefmt=TABLE_FORMAT,
                headers=["SERVICE", "VARIABLE", "LAST CHANGE", "SCORE"],
            )
        )

    # In this case a service is asked to be updated
    else:

        if random:
            new_password = get_random_password()
        elif not new_password:
            print_and_exit("Please specify one between --random and --password options")

        # log.critical(new_password)

        compose = Compose(Application.data.files)
        if SWARM_MODE:
            swarm = Swarm()
            running_services = swarm.get_running_services(Configuration.project)
        else:
            running_services = compose.get_running_services(Configuration.project)

        variables = get_service_passwords(service)
        new_variables = {variable: new_password for variable in variables}

        # Some services can only be updated if already running,
        # others can be updated even if offline,
        # but in every case if the stack is running it has to be restarted

        if service == Services.registry:
            docker = Docker()
            is_running = docker.ping_registry(do_exit=False)
        else:
            is_running = service.value in running_services

        is_running_needed = False

        if service == Services.redis:
            is_running_needed = False
        elif service == Services.flower:
            is_running_needed = False
        elif service == Services.registry:
            is_running_needed = False

        elif service == Services.backend:
            is_running_needed = True
        elif service == Services.neo4j:
            is_running_needed = True
        elif service == Services.postgres:
            is_running_needed = True
        elif service == Services.mariadb:
            is_running_needed = True
        elif service == Services.mongodb:
            is_running_needed = True
        elif service == Services.rabbit:
            is_running_needed = True
        else:  # pragma: no cover
            print_and_exit("Unexpected error, unknown service {}", service.value)

        log.info("Changing password for {}...", service.value)

        if is_running_needed and not is_running:
            print_and_exit(
                "Can't update {} since it is not running. Please start your stack",
                service.value,
            )

        if is_running_needed:
            print_and_exit("Change password for {} not implemented yet", service.value)

        update_projectrc(new_variables)

        # here specific operation have to be implemented.
        # - Nothing for Redis and Flower, projectrc update is enough

        # DEBUG CODE!!
        import time

        time.sleep(1)

        if is_running:
            log.info("{} was running, restarting services...", service.value)

            if service == Services.registry:
                port = Application.env["REGISTRY_PORT"]

                compose.docker.container.remove(REGISTRY, force=True)
                # compose v2 does not implement volatile container yet
                compose_v1 = ComposeV1(files=Application.data.files)
                Configuration.FORCE_COMPOSE_ENGINE = True
                # init is needed to reload the configuration to force compose engine
                Application.get_controller().controller_init()

                compose_v1.create_volatile_container(
                    REGISTRY, detach=True, publish=[f"{port}:{port}"]
                )
            elif SWARM_MODE:

                compose.dump_config(Application.data.services)
                swarm.deploy()

            else:
                compose.start_containers(Application.data.services)
        else:
            log.info("{} was not running, restart is not needed", service.value)

        log.info(
            "The password of {} has been changed. "
            "Please find the new password into your .projectrc file as {} variable",
            service.value,
            variables[0],
        )
