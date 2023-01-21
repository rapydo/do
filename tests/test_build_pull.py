"""
This module will test the build and pull commands
"""
import os
from pathlib import Path

from faker import Faker
from git import Repo

from controller import __version__, colors
from controller.app import Configuration
from tests import (
    Capture,
    create_project,
    exec_command,
    execute_outside,
    init_project,
    random_project_name,
    start_registry,
)


def test_all(capfd: Capture, faker: Faker) -> None:

    execute_outside(capfd, "pull")
    execute_outside(capfd, "build")

    project2 = random_project_name(faker)
    create_project(
        capfd=capfd,
        name="testbuild",
        auth="no",
        frontend="no",
        services=["redis"],
    )
    init_project(capfd)
    create_project(
        capfd=capfd,
        name=project2,
        auth="no",
        frontend="no",
        services=["redis"],
    )

    if Configuration.swarm_mode:

        exec_command(
            capfd,
            "pull",
            "Registry 127.0.0.1:5000 not reachable.",
        )

        exec_command(
            capfd,
            "build",
            "docker buildx is installed",
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
        "-e ACTIVATE_REDIS=0 pull --quiet redis",
        "No such service: redis",
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
    # A true test on such parameter would be quite complex...
    exec_command(
        capfd,
        "pull --all --quiet backend",
        "Images pulled from docker hub",
    )

    # Add a custom image to extend base redis image:
    with open("projects/testbuild/confs/commons.yml", "a") as f:
        f.write(
            """
services:
  redis:
    build: ${PROJECT_DIR}/builds/redis
    image: testbuild/redis:${RAPYDO_VERSION}

    """
        )

    # Missing folder
    exec_command(
        capfd,
        "build redis",
        "docker buildx is installed",
        "Build path not found",
    )

    os.makedirs("projects/testbuild/builds/redis")

    # Missing Dockerfile
    exec_command(
        capfd,
        "build redis",
        "docker buildx is installed",
        "Build path not found: ",
        "projects/testbuild/builds/redis/Dockerfile",
    )

    # Empty Dockerfile
    with open("projects/testbuild/builds/redis/Dockerfile", "w+") as f:
        pass
    exec_command(
        capfd,
        "build redis",
        "docker buildx is installed",
        "Invalid Dockerfile, no base image found in ",
        "projects/testbuild/builds/redis/Dockerfile",
    )

    # Missing base image
    with open("projects/testbuild/builds/redis/Dockerfile", "w+") as f:
        f.write("RUN ls")
    exec_command(
        capfd,
        "build redis",
        "docker buildx is installed",
        "Invalid Dockerfile, no base image found in ",
        "projects/testbuild/builds/redis/Dockerfile",
    )

    # Invalid RAPyDo template
    with open("projects/testbuild/builds/redis/Dockerfile", "w+") as f:
        f.write("FROM rapydo/invalid")
    exec_command(
        capfd,
        "build redis",
        "docker buildx is installed",
        "Unable to find rapydo/invalid in this project",
        "Please inspect the FROM image in",
        "projects/testbuild/builds/redis/Dockerfile",
    )

    image = f"testbuild/redis:${__version__}"
    exec_command(
        capfd,
        "start",
        f" image, execute {colors.RED}rapydo build redis",
    )

    # Not a RAPyDo child but build is possibile
    with open("projects/testbuild/builds/redis/Dockerfile", "w+") as f:
        f.write("FROM ubuntu")
    exec_command(
        capfd,
        "build redis",
        "docker buildx is installed",
        "Custom images built",
    )

    with open("projects/testbuild/builds/redis/Dockerfile", "w+") as f:
        f.write(
            f"""
FROM rapydo/redis:{__version__}
# Just a simple command to differentiate from the parent
RUN mkdir xyz
"""
        )

    r = Repo(".")
    r.git.add("-A")
    r.git.commit("-a", "-m", "'fake'")

    exec_command(
        capfd,
        "build redis",
        "docker buildx is installed",
        f"naming to docker.io/testbuild/redis:{__version__}",
        "Custom images built",
    )

    test_file = Path("projects/testbuild/builds/redis/test")
    with open(test_file, "w+") as f:
        f.write("test")

    exec_command(
        capfd,
        "check -i main --no-git",
        "Can't retrieve a commit history for ",
        "Checks completed",
    )

    test_file.unlink()

    exec_command(
        capfd,
        f"-e ACTIVATE_REDIS=0 -p {project2} build --core redis",
        "No such service: redis",
    )

    # Rebuild core redis image => custom redis is now obsolete
    # Please note the use of the project 2.
    # This way we prevent to rebuilt the custom image of testbuild
    # This simulate a pull updating a core image making the custom image obsolete

    if Configuration.swarm_mode:
        swarm_push_warn = "Local registry push is not implemented yet for core images"
    else:
        swarm_push_warn = ""

    exec_command(
        capfd,
        f"-p {project2} build --core redis",
        "Core images built",
        swarm_push_warn,
        "No custom images to build",
    )
    exec_command(
        capfd,
        "check -i main --no-git",
        f"Obsolete image testbuild/redis:{__version__}",
        "built on ",
        " that changed on ",
        f"Update it with: {colors.RED}rapydo build redis",
    )

    # Add a second service with the same image to test redundant builds
    with open("projects/testbuild/confs/commons.yml", "a") as f:
        f.write(
            """
  redis2:
    build: ${PROJECT_DIR}/builds/redis
    image: testbuild/redis:${RAPYDO_VERSION}

    """
        )

    fin = open("submodules/do/controller/builds/backend/Dockerfile", "a")
    fin.write("xyz")
    fin.close()
    r = Repo("submodules/do")
    r.git.commit("-a", "-m", "'fake'")
    exec_command(
        capfd,
        "check -i main",
        f"Obsolete image rapydo/backend:{__version__}",
        "built on ",
        " but changed on ",
        f"Update it with: {colors.RED}rapydo pull backend",
    )

    exec_command(capfd, "remove", "Stack removed")

    # Add a third service without a build to verify that pull includes it
    # to be the base image even if defined in custom part
    with open("projects/testbuild/confs/commons.yml", "a") as f:
        f.write(
            """
  redis3:
    image: alpine:latest
    environment:
      ACTIVATE: 1
    """
        )

    exec_command(
        capfd,
        "pull --quiet redis3",
        "Base images pulled from docker hub",
    )

    # Now this should fail because pull does not include custom services
    exec_command(
        capfd,
        "start redis3",
        "Stack started",
    )
