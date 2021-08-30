"""
This module will test the build and pull commands
"""
import os

from faker import Faker
from git import Repo

from controller import SWARM_MODE, __version__, colors
from tests import (
    Capture,
    create_project,
    exec_command,
    init_project,
    random_project_name,
    start_registry,
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

    if SWARM_MODE:

        exec_command(
            capfd,
            "pull",
            "Registry 127.0.0.1:5000 not reachable.",
        )

        exec_command(
            capfd,
            "build",
            "Registry 127.0.0.1:5000 not reachable.",
        )

        start_registry(capfd)

    image = f"rapydo/backend:{__version__}"
    exec_command(
        capfd,
        "start",
        f"Missing {image} image, execute {colors.RED}rapydo pull backend",
    )

    exec_command(
        capfd,
        "-e ACTIVATE_RABBIT=0 pull --quiet rabbit",
        "No such service: rabbit",
    )

    exec_command(
        capfd,
        "pull --quiet proxy",
        "No such service: proxy",
    )

    exec_command(
        capfd,
        "pull --quiet",
        "Base images pulled from docker hub",
    )

    # Basic pull
    exec_command(
        capfd,
        "pull xxx",
        "No such service: xxx",
    )

    # --all is useless here... added just to include the parameter in some tests.
    # A true test on such parameter would be quite complicated...
    exec_command(
        capfd,
        "pull --all --quiet backend",
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
        "build rabbit",
        "Build path not found",
    )

    os.makedirs("projects/testbuild/builds/rabbit")

    # Missing Dockerfile
    exec_command(
        capfd,
        "build rabbit",
        "Build path not found: ",
        "projects/testbuild/builds/rabbit/Dockerfile",
    )

    # Empty Dockerfile
    with open("projects/testbuild/builds/rabbit/Dockerfile", "w+") as f:
        pass
    exec_command(
        capfd,
        "build rabbit",
        "Invalid Dockerfile, no base image found in ",
        "projects/testbuild/builds/rabbit/Dockerfile",
    )

    # Missing base image
    with open("projects/testbuild/builds/rabbit/Dockerfile", "w+") as f:
        f.write("RUN ls")
    exec_command(
        capfd,
        "build rabbit",
        "Invalid Dockerfile, no base image found in ",
        "projects/testbuild/builds/rabbit/Dockerfile",
    )

    # Invalid RAPyDo template
    with open("projects/testbuild/builds/rabbit/Dockerfile", "w+") as f:
        f.write("FROM rapydo/invalid")
    exec_command(
        capfd,
        "build rabbit",
        "Unable to find rapydo/invalid in this project",
        "Please inspect the FROM image in",
        "projects/testbuild/builds/rabbit/Dockerfile",
    )

    image = f"testbuild/rabbit:${__version__}"
    exec_command(
        capfd,
        "start",
        f" image, execute {colors.RED}rapydo build rabbit",
    )

    # Not a RAPyDo child but build is possibile
    with open("projects/testbuild/builds/rabbit/Dockerfile", "w+") as f:
        f.write("FROM ubuntu")
    exec_command(
        capfd,
        "build rabbit",
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
        "build rabbit",
        f"naming to docker.io/testbuild/rabbit:{__version__}",
        "Custom images built",
    )

    exec_command(
        capfd,
        f"-e ACTIVATE_RABBIT=0 -p {project2} build --core rabbit",
        "No such service: rabbit",
    )

    # Rebuild core rabbit image => custom rabbit is now obsolete
    # Please note the use of the project 2.
    # This way we prevent to rebuilt the custom image of testbuild
    # This simulate a pull updating a core image making the custom image obsolete
    exec_command(
        capfd,
        f"-p {project2} build --core rabbit",
        "Core images built",
        "No custom images to build",
    )
    exec_command(
        capfd,
        "check -i main --no-git",
        f"Obsolete image testbuild/rabbit:{__version__}",
        "built on ",
        " that changed on ",
        "Update it with: rapydo build rabbit",
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
        "Update it with: rapydo pull backend",
    )

    exec_command(capfd, "remove", "Stack removed")

    # Add a third service without a build to verify that pull includes it
    # to be the base image even if defined in custom part
    with open("projects/testbuild/confs/commons.yml", "a") as f:
        f.write(
            """
  rabbit3:
    image: alpine:latest
    environment:
      ACTIVATE: 1
    """
        )

    exec_command(
        capfd,
        "pull --quiet rabbit3",
        "Base images pulled from docker hub",
    )

    # Now this should fail because pull does not include custom services
    exec_command(
        capfd,
        "start rabbit3",
        "Stack started",
    )
