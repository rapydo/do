"""
This module will test the build and pull commands
"""
import os

from faker import Faker
from git import Repo

from controller import __version__
from tests import Capture, create_project, exec_command, random_project_name


def test_all(capfd: Capture, faker: Faker) -> None:

    project2 = random_project_name(faker)
    create_project(
        capfd=capfd,
        name="testbuild",
        auth="postgres",
        frontend="no",
        services=["rabbit"],
        init=True,
        pull=False,
        start=False,
    )
    create_project(
        capfd=capfd,
        name=project2,
        auth="postgres",
        frontend="no",
        services=["rabbit"],
        init=False,
        pull=False,
        start=False,
    )

    image = f"rapydo/rabbitmq:{__version__}"
    exec_command(
        capfd,
        "-s rabbit start",
        f"Missing {image} image for rabbit service, execute rapydo pull",
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
        "Invalid service name: xxx",
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
    image: myproject/rabbit:${RAPYDO_VERSION}

    """
        )

    os.makedirs("projects/testbuild/builds/rabbit")

    # Missing Dockerfile
    exec_command(
        capfd,
        "-s rabbit build",
        "No such file or directory: ",
        "projects/testbuild/builds/rabbit/Dockerfile",
    )

    # Empty Dockerfile
    with open("projects/testbuild/builds/rabbit/Dockerfile", "w+") as f:
        pass
    exec_command(
        capfd,
        "-s rabbit build",
        "Build failed, is ",
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

    # Not a RAPyDo child
    with open("projects/testbuild/builds/rabbit/Dockerfile", "w+") as f:
        f.write("FROM ubuntu")
    exec_command(
        capfd,
        "-s rabbit build",
        "No custom images to build",
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

    image = f"myproject/rabbit:${__version__}"
    exec_command(
        capfd,
        "-s rabbit start",
        # f"Missing {image} image for rabbit service, execute rapydo build",
        " image for rabbit service, execute rapydo build",
    )

    # Selected a very fast service to speed up tests
    # Build custom rabbit image from pulled image
    exec_command(
        capfd,
        "-s rabbit build",
        f"naming to docker.io/testbuild/rabbit:{__version__}",
        "Custom images built",
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
    image: myproject/rabbit:${RAPYDO_VERSION}

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
