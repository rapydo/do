"""
This module will test the ssl and dhparam commands
"""
import time

from tests import create_project, exec_command


def test_all(capfd, fake):

    create_project(
        capfd=capfd,
        name=fake.word(),
        auth="postgres",
        frontend="no",
        services=["rabbit", "neo4j"],
        # --add-optionals ??
        init=True,
        pull=False,
        start=False,
    )

    exec_command(
        capfd,
        "--prod pull",
        "Base images pulled from docker hub",
    )

    exec_command(
        capfd,
        "ssl",
        "No container found for proxy_1",
    )

    # Before creating SSL certificates, neo4j and rabbit should not be able to start
    exec_command(
        capfd,
        "volatile neo4j",
        "SSL mandatory file not found: /ssl/real/fullchain1.pem",
    )

    exec_command(
        capfd,
        "volatile rabbit",
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

    # Start neo4j and rabbit to verify certificate creation while services are running
    exec_command(
        capfd,
        "--prod -s rabbit,neo4j start",
    )

    # ARGHHH!!! But it is needed because the next command need rabbit already started
    # And it takes some time to make the server up and running
    # Otherwise will fail with:
    # Error: unable to perform an operation on node 'rabbit@rabbit'.
    # Please see diagnostics information and suggestions below.

    # To be replaced with a rapydo verify?
    time.sleep(10)

    exec_command(
        capfd,
        # --no-tty is needed on GitHub Actions
        # to be able to execute commands on the running containers
        "ssl --volatile --no-tty",
        "Creating a self signed SSL certificate",
        "Self signed SSL certificate successfully created",
        "Neo4j is running, but it will reload the certificate by itself",
        "RabbitMQ is running, executing command to refresh the certificate",
        "New certificate successfully installed",
    )
    # Shutoff services, only started to verify certificate creation
    # exec_command(
    #     capfd,
    #     "-s rabbit,neo4j remove",
    # )

    exec_command(
        capfd,
        "ssl --force",
        "No container found for proxy_1",
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

    pconf = "projects/first/project_configuration.yaml"
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
        "ssl --chain-file {f} --key-file {f}".format(f=pconf),
        "Unable to automatically perform the requested operation",
        "You can execute the following commands by your-self:",
    )

    exec_command(
        capfd,
        "dhparam",
        "No container found for proxy_1",
    )

    exec_command(capfd, "remove --all", "Stack removed")
