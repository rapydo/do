"""
This module will test the build and ancestors commands
"""
import os

from git import Repo

from controller import __version__
from controller.dockerizing import Dock
from tests import create_project, exec_command, random_project_name


def test_all(capfd, fake):

    project2 = random_project_name(fake)
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
    image: ${COMPOSE_PROJECT_NAME}/rabbit:${RAPYDO_VERSION}

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
            """
FROM rapydo/rabbitmq:{}
# Just a simple command to differentiate from the parent
RUN mkdir xyz
""".format(
                __version__
            )
        )

    r = Repo(".")
    r.git.add("-A")
    r.git.commit("-a", "-m", "'fake'")

    # Selected a very fast service to speed up tests
    # Build custom rabbit image from pulled image
    exec_command(
        capfd,
        "-s rabbit build",
        "Successfully built",
        f"Successfully tagged testbuild/rabbit:{__version__}",
        "Custom images built",
    )

    exec_command(
        capfd,
        "ancestors XYZ",
        "No child found for XYZ",
    )

    dock = Dock()
    img = dock.images().pop(0)
    # sha256:c1a845de80526fcab136f9fab5f83BLABLABLABLABLA
    img_id = dock.image_info(img).get("Id")
    # => c1a845de8052
    img_id = img_id[7:19]
    exec_command(
        capfd,
        f"ancestors {img_id}",
        f"Finding all children and (grand)+ children of {img_id}",
    )

    # sha256:c1a845de80526fcab136f9fab5f83BLABLABLABLABLA
    img_id = dock.image_info(f"rapydo/rabbitmq:{__version__}").get("Id")
    # => c1a845de8052
    img_id = img_id[7:19]
    # rapydo/rabbitmq has a child: testbuild/rabbit just created
    exec_command(
        capfd,
        f"ancestors {img_id}",
        f"Finding all children and (grand)+ children of {img_id}",
        "testbuild/rabbit",
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

    # rabbit images has no longer any child because it is just rebuilt
    exec_command(
        capfd,
        f"ancestors {img_id}",
        f"Finding all children and (grand)+ children of {img_id}",
    )

    # Add a second service with the same image to test redundant builds
    with open("projects/testbuild/confs/commons.yml", "a") as f:
        f.write(
            """
  rabbit2:
    build: ${PROJECT_DIR}/builds/rabbit
    image: ${COMPOSE_PROJECT_NAME}/rabbit:${RAPYDO_VERSION}

    """
        )

    exec_command(
        capfd,
        "-s rabbit,rabbit2 build",
        "Cannot determine build priority between rabbit and rabbit2",
        "Removed redundant builds from ['rabbit', 'rabbit2'] -> ['rabbit2']",
    )

    # Let's test builds with running containers
    exec_command(capfd, "-s rabbit start")

    you_asked = f"You asked to build testbuild/rabbit:{__version__}"
    but_running = "but the following containers are running: rabbit"
    do_you_want_to = "Do you want to continue? y/n:"

    exec_command(
        capfd,
        "-s rabbit build",
        you_asked,
        but_running,
        do_you_want_to,
        "Unknown response invalid, respond yes or no",
        "Build aborted",
        input_text="invalid\nno\n",
    )

    exec_command(
        capfd,
        "-s rabbit build",
        you_asked,
        but_running,
        do_you_want_to,
        "Build aborted",
        input_text="no\n",
    )
    exec_command(
        capfd,
        "-s rabbit build",
        you_asked,
        but_running,
        do_you_want_to,
        "Build aborted",
        input_text="n\n",
    )
    exec_command(
        capfd,
        "-s rabbit build",
        you_asked,
        but_running,
        do_you_want_to,
        "Build aborted",
        input_text="N\n",
    )
    exec_command(
        capfd,
        "-s rabbit build",
        you_asked,
        but_running,
        do_you_want_to,
        "Build aborted",
        input_text="NO\n",
    )
    exec_command(
        capfd,
        "-s rabbit build",
        you_asked,
        but_running,
        do_you_want_to,
        "Successfully built",
        input_text="y\n",
    )
    exec_command(
        capfd,
        "-s rabbit build",
        you_asked,
        but_running,
        do_you_want_to,
        "Successfully built",
        input_text="yes\n",
    )
    exec_command(
        capfd,
        "-s rabbit build",
        you_asked,
        but_running,
        do_you_want_to,
        "Successfully built",
        input_text="Y\n",
    )
    exec_command(
        capfd,
        "-s rabbit build",
        you_asked,
        but_running,
        do_you_want_to,
        "Successfully built",
        input_text="YES\n",
    )
    exec_command(
        capfd,
        "-s rabbit build --yes",
        "Successfully built",
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
