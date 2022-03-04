from typing import Optional, Tuple

from controller import log, print_and_exit
from controller.deploy.docker import Docker

SERVICE_NAME = __name__
EXPECTED_EXT = ".sql.gz"


def restore(
    container: Optional[Tuple[str, str]], backup_file: str, force: bool
) -> None:

    if not container:
        print_and_exit(
            "The restore procedure requires {} running, please start your stack",
            SERVICE_NAME,
        )

    docker = Docker()

    log.info("Starting restore on {}...", SERVICE_NAME)

    backup_path = f"/backup/{SERVICE_NAME}/{backup_file}"
    dump_file = backup_file.replace(".gz", "")
    dump_path = f"/tmp/{dump_file}"

    docker.exec_command(container, user="root", command=f"cp {backup_path} /tmp/")

    docker.exec_command(
        container, user="root", command=f"gunzip -kf /tmp/{backup_file}"
    )

    # Executed as root
    docker.exec_command(container, user="root", command=f"chown postgres {dump_path}")

    # By using pg_dumpall the resulting dump can be restored with psql:
    docker.exec_command(
        container,
        user="postgres",
        command=f"psql -U sqluser -f {dump_path} postgres",
    )

    log.info("Restore from data{} completed", backup_path)
