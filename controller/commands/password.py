"""
Manage services passwords
"""
import re
from datetime import date, datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Tuple, cast

import typer
from tabulate import tabulate
from zxcvbn import zxcvbn  # type: ignore

from controller import (
    GREEN,
    PLACEHOLDER,
    PROJECTRC,
    RED,
    REGISTRY,
    TABLE_FORMAT,
    log,
    print_and_exit,
)
from controller.app import Application, Configuration
from controller.commands import PASSWORD_MODULES
from controller.deploy.docker import Docker
from controller.templating import Templating, get_strong_password

# make this configurable
PASSWORD_EXPIRATION = 90

UPDATE_LABEL = "updated on"


# Enum() expects a string, tuple, list or dict literal as the second argument
# https://github.com/python/mypy/issues/5317
SupportedServices = Enum(  # type: ignore
    "SupportedServices", {name: name for name in sorted(PASSWORD_MODULES.keys())}
)


# Note: can't directly extract yaml with comments because it is not supported
# https://github.com/yaml/pyyaml/issues/90
def parse_projectrc() -> Dict[str, datetime]:

    if not PROJECTRC.exists():
        return {}

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
                    rf".*{UPDATE_LABEL} (20[0-9][0-9]-[0-1][0-9]-[0-3][0-9])$",
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


def get_expired_passwords() -> List[Tuple[str, datetime]]:
    expired_passwords: List[Tuple[str, datetime]] = []

    last_updates = parse_projectrc()
    now = datetime.now()

    for s in PASSWORD_MODULES:
        # This should never happens and can't be (easily) tested
        if s not in Application.data.base_services:  # pragma: no cover
            print_and_exit("Command misconfiguration, unknown {} service", s)

        if s != REGISTRY and s not in Application.data.active_services:
            continue

        if s == REGISTRY and not Configuration.swarm_mode:
            continue

        module = PASSWORD_MODULES.get(s)

        if not module:  # pragma: no cover
            print_and_exit(f"{s} misconfiguration, module not found")

        for variable in module.PASSWORD_VARIABLES:

            if variable in last_updates:
                change_date = last_updates.get(variable, datetime.fromtimestamp(0))
                expiration_date = change_date + timedelta(days=PASSWORD_EXPIRATION)
                if now > expiration_date:
                    expired_passwords.append(
                        (
                            variable,
                            expiration_date,
                        )
                    )
    return expired_passwords


@Application.app.command(help="Manage services passwords")
def password(
    service: SupportedServices = typer.Argument(None, help="Service name"),
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
        for s in PASSWORD_MODULES:
            # This should never happens and can't be (easily) tested
            if s not in Application.data.base_services:  # pragma: no cover
                print_and_exit("Command misconfiguration, unknown {} service", s)

            if s != REGISTRY and s not in Application.data.active_services:
                continue

            if s == REGISTRY and not Configuration.swarm_mode:
                continue

            module = PASSWORD_MODULES.get(s)

            if not module:  # pragma: no cover
                print_and_exit(f"{s} misconfiguration, module not found")

            for variable in module.PASSWORD_VARIABLES:

                password = Application.env.get(variable)

                if password == PLACEHOLDER:
                    score = None
                else:
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

                pass_line.append(s)
                pass_line.append(variable)

                if expired:
                    pass_line.append(RED(last_change))
                else:
                    pass_line.append(GREEN(last_change))

                if score is None:
                    pass_line.append(RED("NOT SET"))
                elif score < MIN_PASSWORD_SCORE:
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

        module = PASSWORD_MODULES.get(service.value)

        if not module:  # pragma: no cover
            print_and_exit(f"{service.value} misconfiguration, module not found")

        if random:
            new_password = get_strong_password()
        elif not new_password:
            print_and_exit("Please specify one between --random and --password options")

        docker = Docker()

        variables = module.PASSWORD_VARIABLES
        old_password = Application.env.get(variables[0])
        new_variables = {variable: new_password for variable in variables}

        # Some services can only be updated if already running,
        # others can be updated even if offline,
        # but in every case if the stack is running it has to be restarted

        if service.value == REGISTRY:
            is_running = docker.registry.ping(do_exit=False)
            container: Optional[Tuple[str, str]] = ("registry", "")
        else:
            container = docker.get_container(service.value)
            is_running = container is not None

        is_running_needed = module.IS_RUNNING_NEEDED

        log.info("Changing password for {}...", service.value)

        if is_running_needed and (not is_running or not container):
            print_and_exit(
                "Can't update {} because it is not running. Please start your stack",
                service.value,
            )

        update_projectrc(new_variables)

        if container:
            module.password(container, old_password, new_password)

        if is_running:
            log.info("{} was running, restarting services...", service.value)

            Application.get_controller().check_placeholders_and_passwords(
                Application.data.compose_config, Application.data.services
            )
            if service.value == REGISTRY:
                port = cast(int, Application.env["REGISTRY_PORT"])

                docker.client.container.remove(REGISTRY, force=True)

                docker.compose.create_volatile_container(
                    REGISTRY, detach=True, publish=[(port, port)]
                )
            elif Configuration.swarm_mode:

                docker.compose.dump_config(Application.data.services)
                docker.swarm.deploy()

            else:
                docker.compose.start_containers(Application.data.services)
        else:
            log.info("{} was not running, restart is not needed", service.value)

        log.info(
            "The password of {} has been changed. "
            "Please find the new password into your .projectrc file as {} variable",
            service.value,
            variables[0],
        )
