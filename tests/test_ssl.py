"""
This module will test the ssl command
"""
import time

from faker import Faker

from controller import SWARM_MODE, colors
from tests import (
    Capture,
    create_project,
    exec_command,
    execute_outside,
    random_project_name,
    service_verify,
    start_registry,
)


def test_all(capfd: Capture, faker: Faker) -> None:

    execute_outside(capfd, "ssl")

    project = random_project_name(faker)
    create_project(
        capfd=capfd,
        name=project,
        auth="neo4j",
        frontend="no",
        services=["rabbit"],
    )
    pconf = f"projects/{project}/project_configuration.yaml"

    exec_command(
        capfd,
        "--prod init -f",
        "Created default .projectrc file",
        "Project initialized",
    )

    start_registry(capfd)

    exec_command(
        capfd,
        "ssl",
        f"image, execute {colors.RED}rapydo pull proxy",
    )

    exec_command(
        capfd,
        "--prod pull --quiet",
        "Base images pulled from docker hub",
    )

    exec_command(
        capfd,
        "ssl",
        "The proxy is not running, start your stack or try with "
        f"{colors.RED}rapydo ssl --volatile",
    )

    # Before creating SSL certificates rabbit and neo4j should not be able to start
    exec_command(
        capfd,
        "run --debug rabbit",
        "SSL mandatory file not found: /ssl/real/fullchain1.pem",
    )

    exec_command(
        capfd,
        "run --debug neo4j",
        "SSL mandatory file not found: /ssl/real/fullchain1.pem",
    )

    exec_command(
        capfd,
        "ssl --volatile",
        "Creating a self signed SSL certificate",
        "Self signed SSL certificate successfully created",
        # Just to verify that the default does not change
        "Generating DH parameters, 1024 bit long safe prime, generator 2",
    )

    # Start to verify certificate creation while services are running
    exec_command(
        capfd,
        "--prod start",
    )

    # Needed because the next command requires rabbit already started
    # Otherwise will fail with:
    # Error: unable to perform an operation on node 'rabbit@rabbit'.
    # Please see diagnostics information and suggestions below.
    if SWARM_MODE:
        # 60!? :| It still fails by raising to 30... Let's double it!!
        time.sleep(60)
        # DEBUG CODE
        exec_command(capfd, "logs rabbit")
    else:
        time.sleep(5)

    service_verify(capfd, "rabbitmq")

    exec_command(
        capfd,
        "ssl --no-tty",
        "--no-tty option is deprecated, you can stop using it",
        "Creating a self signed SSL certificate",
        "Self signed SSL certificate successfully created",
        "Neo4j is running, a full restart is needed. NOT IMPLEMENTED YET.",
        "RabbitMQ is running, executing command to refresh the certificate",
        "New certificate successfully enabled",
    )

    exec_command(
        capfd,
        "ssl --chain-file /file",
        "Invalid chain file (you provided /file)",
    )
    exec_command(
        capfd,
        "ssl --key-file /file",
        "Invalid chain file (you provided none)",
    )

    exec_command(
        capfd,
        f"ssl --chain-file {pconf}",
        "Invalid key file (you provided none)",
    )
    exec_command(
        capfd,
        f"ssl --chain-file {pconf} --key-file /file",
        "Invalid key file (you provided /file)",
    )
    exec_command(
        capfd,
        f"ssl --chain-file {pconf} --key-file {pconf}",
        "Unable to automatically perform the requested operation",
        "You can execute the following commands by your-self:",
    )
