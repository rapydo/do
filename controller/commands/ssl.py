import os

import typer

from controller import log
from controller.app import Application
from controller.compose import Compose


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
        help="Disable pseudo-tty allocation, useful to execute the command from a cronjob",
        show_default=False,
    ),
    chain_file: str = typer.Option(
        None,
        "--chain-file",
        help="Path to existing chain file (.pem format)",
        show_default=False,
    ),
    key_file: str = typer.Option(
        None,
        "--key-file",
        help="Path to existing key file (.pem format)",
        show_default=False,
    ),
):

    if chain_file is not None or key_file is not None:
        if chain_file is None:
            log.exit("Invalid chain file (you provided none)")
        elif not os.path.exists(chain_file):
            log.exit("Invalid chain file (you provided {})", chain_file)

        if key_file is None:
            log.exit("Invalid key file (you provided none)")
        elif not os.path.exists(key_file):
            log.exit("Invalid key file (you provided {})", key_file)

    service = "proxy"

    if chain_file is not None and key_file is not None:

        log.info("Unable to automatically perform the requested operation")
        log.info("You can execute the following commands by your-self:")

        print("")
        print(
            "docker cp {} {}_{}_1:/etc/letsencrypt/real/fullchain1.pem".format(
                chain_file, Application.data.project, service
            )
        )
        print(
            "docker cp {} {}_{}_1:/etc/letsencrypt/real/privkey1.pem".format(
                key_file, Application.data.project, service
            )
        )

        print(f'rapydo shell {service} --command "nginx -s reload"')
        print("")

        return

    command = "/bin/bash updatecertificates"
    if force:
        command = f"{command} --force"

    command = f"{command} {Application.data.hostname}"

    dc = Compose(files=Application.data.files)

    if volatile:
        dc.create_volatile_container(service, command)
    else:
        dc.exec_command(service, user="root", command=command, disable_tty=no_tty)
