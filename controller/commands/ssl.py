import os

from controller import log
from controller.compose import Compose


def __call__(args, project, files, hostname, **kwargs):

    chain = args.get("chain_file")
    key = args.get("key_file")
    no_tty = args.get("no_tty")

    if chain is not None or key is not None:
        if chain is None:
            log.exit("Invalid chain file (you provided none)")
        elif not os.path.exists(chain):
            log.exit("Invalid chain file (you provided {})", chain)

        if key is None:
            log.exit("Invalid key file (you provided none)")
        elif not os.path.exists(key):
            log.exit("Invalid key file (you provided {})", key)

    service = "proxy"

    if chain is not None and key is not None:

        log.info("Unable to automatically perform the requested operation")
        log.info("You can execute the following commands by your-self:")

        print("")
        print(
            "docker cp {} {}_{}_1:/etc/letsencrypt/real/fullchain1.pem".format(
                chain, project, service
            )
        )
        print(
            "docker cp {} {}_{}_1:/etc/letsencrypt/real/privkey1.pem".format(
                key, project, service
            )
        )

        print('rapydo shell {} --command "nginx -s reload"'.format(service))
        print("")

        return True

    command = "/bin/bash updatecertificates"
    if args.get("force"):
        command = "{} --force".format(command)

    command = "{} {}".format(command, hostname)

    dc = Compose(files=files)

    if args.get("volatile"):
        dc.create_volatile_container(service, command)
        return True

    dc.exec_command(service, user="root", command=command, disable_tty=no_tty)
    return True
