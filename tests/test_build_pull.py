"""
This module will test the build and pull commands
"""
import os

from faker import Faker
from git import Repo

from controller import __version__
from tests import (
    Capture,
    create_project,
    exec_command,
    init_project,
    random_project_name,
)


def test_all(capfd: Capture, faker: Faker) -> None:

    project2 = random_project_name(faker)
    create_project(
        capfd=capfd,
        name="testbuild",
        auth="postgres",
        frontend="no",
        services=["rabbit"],
    )
    init_project(capfd)
    create_project(
        capfd=capfd,
        name=project2,
        auth="postgres",
        frontend="no",
        services=["rabbit"],
    )

    image = f"rapydo/rabbitmq:{__version__}"
    exec_command(
        capfd,
        "-s rabbit start",
        f"Missing {image} image for rabbit service, execute rapydo pull",
    )

    exec_command(
        capfd,
        "-e ACTIVATE_RABBIT=0 -s rabbit pull --quiet",
        "Configuration error: rabbit service is not enabled",
    )

    exec_command(
        capfd,
        "-s proxy pull --quiet",
        "Configuration error: proxy service is not enabled",
    )

    exec_command(
        capfd,
        "-s rabbit pull --quiet",
        "Base images pulled from docker hub",
    )

    # Basic pull
    exec_command(
        capfd,
        "-s xxx pull",
        "Configuration error: xxx service is not enabled",
    )

    # --all is useless here... added just to include the parameter in some tests.
    # A true test on such parameter would be quite complicated...
    exec_command(
        capfd,
        "-s backend pull --all --quiet",
        "Images pulled from docker hub",
    )

    # Add a custom image to extend base rabbit image:
    with open("projects/testbuild/confs/commons.yml", "a") as f:
        f.write(
            """
services:
  rabbit:
    build: ${PROJECT_DIR}/builds/rabbit
    image: testbuild/rabbit:${RAPYDO_VERSION}

    """
        )

    # Missing folder
    exec_command(
        capfd,
        "-s rabbit build",
        # Errors from docker compose
        " either does not exist, is not accessible, or is not a valid URL.",
    )

    os.makedirs("projects/testbuild/builds/rabbit")

    # Missing Dockerfile
    exec_command(
        capfd,
        "-s rabbit build",
        "Build path not found: ",
        "projects/testbuild/builds/rabbit/Dockerfile",
    )

    # Empty Dockerfile
    with open("projects/testbuild/builds/rabbit/Dockerfile", "w+") as f:
        pass
    exec_command(
        capfd,
        "-s rabbit build",
        "Invalid build, is ",
        "projects/testbuild/builds/rabbit/Dockerfile empty?",
    )

    # Missing base image
    with open("projects/testbuild/builds/rabbit/Dockerfile", "w+") as f:
        f.write("RUN ls")
    exec_command(
        capfd,
        "-s rabbit build",
        "No base image found ",
        "projects/testbuild/builds/rabbit/Dockerfile, unable to build",
    )

    # Invalid RAPyDo template
    with open("projects/testbuild/builds/rabbit/Dockerfile", "w+") as f:
        f.write("FROM rapydo/invalid")
    exec_command(
        capfd,
        "-s rabbit build",
        "Unable to find rapydo/invalid in this project",
        "Please inspect the FROM image in",
        "projects/testbuild/builds/rabbit/Dockerfile",
    )

    image = f"testbuild/rabbit:${__version__}"
    exec_command(
        capfd,
        "-s rabbit start",
        # f"Missing {image} image for rabbit service, execute rapydo build",
        " image for rabbit service, execute rapydo build",
    )

    # Not a RAPyDo child but build is possibile
    with open("projects/testbuild/builds/rabbit/Dockerfile", "w+") as f:
        f.write("FROM ubuntu")
    exec_command(
        capfd,
        "-s rabbit build",
        "Custom images built",
    )

    with open("projects/testbuild/builds/rabbit/Dockerfile", "w+") as f:
        f.write(
            f"""
FROM rapydo/rabbitmq:{__version__}
# Just a simple command to differentiate from the parent
RUN mkdir xyz
"""
        )

    r = Repo(".")
    r.git.add("-A")
    r.git.commit("-a", "-m", "'fake'")

    exec_command(
        capfd,
        "-s rabbit build",
        f"naming to docker.io/testbuild/rabbit:{__version__}",
        "Custom images built",
    )

    exec_command(
        capfd,
        f"-e ACTIVATE_RABBIT=0 -p {project2} -s rabbit build --core",
        "Configuration error: rabbit service is not enabled",
    )

    # Rebuild core rabbit image => custom rabbit is now obsolete
    # Please note the use of the project 2.
    # This way we prevent to rebuilt the custom image of testbuild
    # This simulate a pull updating a core image making the custom image obsolete
    exec_command(
        capfd,
        f"-p {project2} -s rabbit build --core",
        "Core images built",
        "No custom images to build",
    )
    exec_command(
        capfd,
        "check -i main --no-git",
        f"Obsolete image testbuild/rabbit:{__version__}",
        "built on ",
        " that changed on ",
        "Update it with: rapydo --services rabbit build",
    )

    # Add a second service with the same image to test redundant builds
    with open("projects/testbuild/confs/commons.yml", "a") as f:
        f.write(
            """
  rabbit2:
    build: ${PROJECT_DIR}/builds/rabbit
    image: testbuild/rabbit:${RAPYDO_VERSION}

    """
        )

    fin = open("submodules/build-templates/backend/Dockerfile", "a")
    fin.write("xyz")
    fin.close()
    r = Repo("submodules/build-templates")
    r.git.commit("-a", "-m", "'fake'")
    exec_command(
        capfd,
        "check -i main",
        f"Obsolete image rapydo/backend:{__version__}",
        "built on ",
        " but changed on ",
        "Update it with: rapydo --services backend pull",
    )

    exec_command(capfd, "remove --all", "Stack removed")
