"""
This module will test the ssl command
"""
from faker import Faker

from controller import SWARM_MODE, colors
from tests import (
    Capture,
    create_project,
    exec_command,
    random_project_name,
    service_verify,
)


def test_all(capfd: Capture, faker: Faker) -> None:

    if SWARM_MODE:
        return None

    project = random_project_name(faker)
    create_project(
        capfd=capfd,
        name=project,
        auth="postgres",
        frontend="no",
        services=["rabbit", "neo4j"],
    )
    pconf = f"projects/{project}/project_configuration.yaml"

    exec_command(
        capfd,
        "--prod init -f",
        "Created default .projectrc file",
        "Project initialized",
    )

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
        "No container found for proxy_1",
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

    service_verify(capfd, "rabbitmq")

    exec_command(
        capfd,
        # --no-tty is needed on GitHub Actions
        # to be able to execute commands on the running containers
        "ssl --no-tty",
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
