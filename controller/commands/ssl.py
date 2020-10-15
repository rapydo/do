from pathlib import Path

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
    force: bool = typer.Option(
        False,
        "--force",
        help="Force Let's Encrypt to renew the certificate",
        show_default=False,
    ),
    no_tty: bool = typer.Option(
        False,
        "--no-tty",
        help="Disable pseudo-tty allocation (e.g. to execute from a cronjob)",
        show_default=False,
    ),
    chain_file: Path = typer.Option(
        None,
        "--chain-file",
        help="Path to existing chain file (.pem format)",
        show_default=False,
    ),
    key_file: Path = typer.Option(
        None,
        "--key-file",
        help="Path to existing key file (.pem format)",
        show_default=False,
    ),
):
    Application.controller.controller_init()

    if chain_file is not None or key_file is not None:
        if chain_file is None:
            log.exit("Invalid chain file (you provided none)")
        elif not chain_file.exists():
            log.exit("Invalid chain file (you provided {})", chain_file)

        if key_file is None:
            log.exit("Invalid key file (you provided none)")
        elif not key_file.exists():
            log.exit("Invalid key file (you provided {})", key_file)

    service = "proxy"

    if chain_file is not None and key_file is not None:

        log.info("Unable to automatically perform the requested operation")
        log.info("You can execute the following commands by your-self:")

        print("")
        print(
            "docker cp {} {}_{}_1:/etc/letsencrypt/real/fullchain1.pem".format(
                chain_file, Configuration.project, service
            )
        )
        print(
            "docker cp {} {}_{}_1:/etc/letsencrypt/real/privkey1.pem".format(
                key_file, Configuration.project, service
            )
        )

        print(f'rapydo shell {service} "nginx -s reload"')
        print("")

        return

    command = "/bin/bash updatecertificates"
    if force:
        command = f"{command} --force"

    command = f"{command} {Configuration.hostname}"

    dc = Compose(files=Application.data.files)

    if volatile:
        dc.create_volatile_container(service, command=command)
    else:
        dc.exec_command(service, user="root", command=command, disable_tty=no_tty)
