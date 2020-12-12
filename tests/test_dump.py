"""
This module will test the dump command
"""


from tests import create_project, exec_command


def test_dump(capfd, fake):

    create_project(
        capfd=capfd,
        name=fake.word(),
        auth="postgres",
        frontend="angular",
        services=["rabbit", "neo4j"],
        init=True,
        pull=True,
        start=False,
    )

    exec_command(
        capfd,
        "dump",
        "Config dump: docker-compose.yml",
    )
