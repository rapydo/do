import sys
from pathlib import Path
from typing import Optional

import typer

from controller import log
from controller.app import Application, Configuration
from controller.compose import Compose

# 0 0 * * 3 cd /home/??? && \
#     COMPOSE_INTERACTIVE_NO_CLI=1 /usr/local/bin/rapydo ssl --no-tty > \
#         /home/???/data/logs/ssl.log 2>&1


@Application.app.command(help="Issue a SSL certificate with Let's Encrypt")
def ssl(
    volatile: bool = typer.Option(
        False,
        "--volatile",
        help="Create a volatile proxy service to request the certificate",
        show_default=False,
    ),
    no_tty: bool = typer.Option(
        False,
        "--no-tty",
        help="Disable pseudo-tty allocation (e.g. to execute from a cronjob)",
        show_default=False,
    ),
    chain_file: Optional[Path] = typer.Option(
        None,
        "--chain-file",
        help="Path to existing chain file (.pem format)",
        show_default=False,
    ),
    key_file: Optional[Path] = typer.Option(
        None,
        "--key-file",
        help="Path to existing key file (.pem format)",
        show_default=False,
    ),
) -> None:
    Application.get_controller().controller_init()

    if chain_file is not None or key_file is not None:
        if chain_file is None:
            Application.exit("Invalid chain file (you provided none)")
        elif not chain_file.exists():
            Application.exit("Invalid chain file (you provided {})", chain_file)

        if key_file is None:
            Application.exit("Invalid key file (you provided none)")
        elif not key_file.exists():
            Application.exit("Invalid key file (you provided {})", key_file)

    service = "proxy"

    if chain_file is not None and key_file is not None:

        log.info("Unable to automatically perform the requested operation")
        log.info("You can execute the following commands by your-self:")

        container = f"{Configuration.project}_{service}_1"
        letsencrypt_path = "/etc/letsencrypt/real"
        print("")
        print(f"docker cp {chain_file} {container}:{letsencrypt_path}/fullchain1.pem")
        print(f"docker cp {key_file} {container}:{letsencrypt_path}/privkey1.pem")
        print(f"rapydo shell {service} 'nginx -s reload'")
        print("")

        return

    command = f"/bin/bash updatecertificates {Configuration.hostname}"

    dc = Compose(files=Application.data.files)

    try:
        if volatile:
            dc.create_volatile_container(service, command=command)
        else:
            dc.exec_command(service, user="root", command=command, disable_tty=no_tty)
    except SystemExit as e:

        if not volatile:
            log.info(
                "If you proxy container is not running, try with rapydo ssl --volatile"
            )
        sys.exit(e.code)
    else:

        running_containers = dc.get_running_containers(Configuration.project)
        if "neo4j" in running_containers:
            # This is not true!! A full restart is needed
            # log.info("Neo4j is running, but it will reload the certificate by itself")
            # But not implemented yet...
            log.info("Neo4j is running, a full restart is needed. NOT IMPLEMENTED YET.")

        if "rabbit" in running_containers:
            log.info(
                "RabbitMQ is running, executing command to refresh the certificate"
            )
            # Please note that Erland is able to automatically reload the certificate
            # But RabbitMQ does not. Probably in the future releases this command will
            # No longer be required. To test it after the creation of the new cert:
            #   echo -n | openssl s_client -showcerts -connect hostname:5671

            # Also note that this command only works if rabbit is executed in PROD mode
            # Otherwise it will fail with the following error:
            #       Error: unable to perform an operation on node 'rabbit@rabbit'.
            #       Please see diagnostics information and suggestions below.
            dc.exec_command(
                "rabbit",
                command="rabbitmqctl eval 'ssl:clear_pem_cache().'",
                disable_tty=no_tty,
            )

        log.info("New certificate successfully enabled")
