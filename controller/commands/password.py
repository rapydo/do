import re
from datetime import date, datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Tuple, cast

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
from controller.app import Application
from controller.deploy.compose_v2 import Compose
from controller.deploy.docker import Docker
from controller.deploy.swarm import Swarm
from controller.templating import Templating, get_strong_password
from controller.utilities import services

# make this configurable
PASSWORD_EXPIRATION = 90

UPDATE_LABEL = "updated on"


class Services(str, Enum):
    backend = "backend"
    neo4j = "neo4j"
    postgres = "postgres"
    mariadb = "mariadb"
    # mongodb = "mongodb"
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
        # return ["ALCHEMY_PASSWORD", "MYSQL_ROOT_PASSWORD"]
        # MYSQL_ROOT_PASSWORD change is not supported yet
        return ["ALCHEMY_PASSWORD"]
    # if service == Services.mongodb:
    #     return ["MONGO_PASSWORD"]
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


def get_projectrc_variables_indentation(projectrc: List[str]) -> int:
    env_indentation = 0
    for line in projectrc:

        # save the indentation level of the env block
        # it will be used to determine the variables indentation
        # if no further lines will be found
        if line.strip().startswith("env:"):
            env_indentation = line.index("env:")
            continue

        # Skip every line before the env block
        if env_indentation == 0:
            continue

        m = re.search(r"^(\s+).*", line)
        if m:
            blanks = len(m.group(1))
            # Skip any lines after env with an indentation lower than env itself
            # (for example a blank line or any other wrong-indented line)
            if blanks < env_indentation:
                continue

            return blanks

    # if reached this point it means that after the env block no further non-empty lines
    # have been found, so return the env level by adding 1 indentation level
    # Add 1 indentation level
    return int(3 * env_indentation / 2)


# Note: can't directly use utilities in app.py because in this case we want to
# maintain all values (not only templated variables) and we also want to keep comments
def update_projectrc(variables: Dict[str, str]) -> None:

    today = date.today().strftime("%Y-%m-%d")
    annotation = f"# {UPDATE_LABEL} {today}"
    with open(PROJECTRC) as f:
        lines = f.readlines()
        append_additional_lines: List[str] = []

        blanks = get_projectrc_variables_indentation(lines)
        if blanks == 0:  # pragma: no cover
            print_and_exit("Malformed .projectrc file, can't find an env block")

        pref = " " * blanks

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


@Application.app.command(help="Manage services passwords")
def password(
    service: Services = typer.Argument(None, help="Service name"),
    show: bool = typer.Option(
        False,
        "--show",
        help="Show the current password(s)",
        show_default=False,
    ),
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

    Application.print_command(
        Application.serialize_parameter("--show", show, IF=show),
        Application.serialize_parameter("--random", random, IF=random),
        Application.serialize_parameter("--password", new_password, IF=new_password),
        Application.serialize_parameter("", service),
    )

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

            if s == Services.registry and not SWARM_MODE:
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

                if show:
                    pass_line.append(str(password))

                table.append(pass_line)

        headers = ["SERVICE", "VARIABLE", "LAST CHANGE", "STRENGTH"]
        if show:
            headers.append("PASSWORD")

        print("")
        print(
            tabulate(
                table,
                tablefmt=TABLE_FORMAT,
                headers=headers,
            )
        )

    # In this case a service is asked to be updated
    else:

        if random:
            new_password = get_strong_password()
        elif not new_password:
            print_and_exit("Please specify one between --random and --password options")

        compose = Compose(Application.data.files)

        variables = get_service_passwords(service)
        old_password = Application.env.get(variables[0])
        new_variables = {variable: new_password for variable in variables}

        # Some services can only be updated if already running,
        # others can be updated even if offline,
        # but in every case if the stack is running it has to be restarted

        docker = Docker()
        if service == Services.registry:
            is_running = docker.ping_registry(do_exit=False)
            container: Optional[Tuple[str, str]] = ("registry", "")
        else:
            container = docker.get_container(service.value)
            is_running = container is not None

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
        # elif service == Services.mongodb:
        #     is_running_needed = True
        elif service == Services.rabbit:
            is_running_needed = True
        else:  # pragma: no cover
            print_and_exit("Unexpected error, unknown service {}", service.value)

        log.info("Changing password for {}...", service.value)

        if is_running_needed and (not is_running or not container):
            print_and_exit(
                "Can't update {} because it is not running. Please start your stack",
                service.value,
            )

        update_projectrc(new_variables)

        if service == Services.backend and container:
            # restapi init need the env variable to be updated but can't be done after
            # the restart because it often fails because unable to re-connect to
            # services in a short time and some long sleep would be needed
            # => applied a workaround to be able to execute it before the restart
            docker.exec_command(
                container,
                user=services.get_default_user(service),
                command=f"""/bin/bash -c '
                    AUTH_DEFAULT_PASSWORD=\"{new_password}\"
                        restapi init --force-user
                    '
                    """,
            )

        elif service == Services.neo4j and container:

            docker.exec_command(
                container,
                user=services.get_default_user(service),
                command=f"""bin/cypher-shell \"
                    ALTER CURRENT USER
                    SET PASSWORD
                    FROM '{old_password}'
                    TO '{new_password}';
                \"""",
            )
        elif service == Services.postgres and container:
            # Interactively:
            # \password username
            # Non interactively:
            # https://ubiq.co/database-blog/how-to-change-user-password-in-postgresql
            user = Application.env.get("ALCHEMY_USER")
            db = Application.env.get("ALCHEMY_DB")
            docker.exec_command(
                container,
                user=services.get_default_user(service),
                command=f"""
                    psql -U {user} -d {db} -c \"
                        ALTER USER {user} WITH PASSWORD \'{new_password}\';
                    \"
                """,
            )

        elif service == Services.mariadb and container:
            # https://dev.mysql.com/doc/refman/8.0/en/set-password.html

            user = Application.env.get("ALCHEMY_USER")
            pwd = Application.env.get("MYSQL_ROOT_PASSWORD")
            db = Application.env.get("ALCHEMY_DB")

            docker.exec_command(
                container,
                user=services.get_default_user(service),
                command=f"""
                    mysql -uroot -p\"{pwd}\" -D\"{db}\" -e
                        "ALTER USER '{user}'@'%' IDENTIFIED BY '{new_password}';"
                    """,
            )
        # elif service == Services.mongodb and container:
        #     # db.changeUserPassword(...)
        #     pass
        elif service == Services.rabbit and container:
            user = Application.env.get("RABBITMQ_USER")
            docker.exec_command(
                container,
                user=services.get_default_user(service),
                command=f'rabbitmqctl change_password "{user}" "{new_password}"',
            )

        if is_running:
            log.info("{} was running, restarting services...", service.value)

            if service == Services.registry:
                port = cast(int, Application.env["REGISTRY_PORT"])

                compose.docker.container.remove(REGISTRY, force=True)

                compose.create_volatile_container(
                    REGISTRY, detach=True, publish=[(port, port)]
                )
            elif SWARM_MODE:

                compose.dump_config(Application.data.services)
                swarm = Swarm()
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
