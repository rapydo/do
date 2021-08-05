from datetime import datetime
from pathlib import Path
from typing import Any, List, Optional, Tuple

import typer

from controller import SWARM_MODE, log, print_and_exit
from controller.app import Application
from controller.deploy.builds import (
    find_templates_build,
    find_templates_override,
    get_image_creation,
)
from controller.deploy.docker import Docker
from controller.deploy.swarm import Swarm
from controller.templating import Templating
from controller.utilities import git

DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


@Application.app.command(help="Verify if current project is compliant to RAPyDo specs")
def check(
    no_git: bool = typer.Option(
        False,
        "--no-git",
        "-s",
        help="Skip checks on git commits",
        show_default=False,
    ),
    no_builds: bool = typer.Option(
        False,
        "--no-builds",
        help="Skip check on docker builds",
        show_default=False,
    ),
    ignore_submodules: List[str] = typer.Option(
        "",
        "--ignore-submodule",
        "-i",
        help="Ignore submodule",
        show_default=False,
        autocompletion=Application.autocomplete_submodule,
    ),
) -> None:

    Application.get_controller().controller_init()

    if SWARM_MODE:
        # This is to verify if swarm is working. It will verify in the constructor
        # if the node has joined a swarm cluster by requesting for a swarm token
        # If not, the execution will halt
        swarm = Swarm()
        # this is true, otherwise during the Swarm initialization the app will be halt
        log.debug("Swarm is correctly initialized")

        swarm.check_resources()

    if no_git:
        log.info("Skipping git checks")
    else:
        log.info("Checking git (skip with --no-git)")
        Application.git_checks(ignore_submodules)

    if no_builds:
        log.info("Skipping builds checks")
    else:
        log.info("Checking builds (skip with --no-builds)")

        docker = Docker()
        dimages = [img.repo_tags[0] for img in docker.client.images() if img.repo_tags]

        all_builds = find_templates_build(Application.data.compose_config)
        core_builds = find_templates_build(Application.data.base_services)
        overriding_builds = find_templates_override(
            Application.data.compose_config, core_builds
        )

        for image_tag, build in all_builds.items():

            if not any(
                x in Application.data.active_services for x in build["services"]
            ):
                continue

            if image_tag not in dimages:
                if image_tag in core_builds:
                    log.warning("Missing {} image, execute rapydo pull", image_tag)
                else:
                    log.warning("Missing {} image, execute rapydo build", image_tag)
                continue

            image_creation = get_image_creation(image_tag)
            # Check if some recent commit modified the Dockerfile
            d1, d2 = build_is_obsolete(image_creation, build)
            if d1 and d2:
                print_obsolete(image_tag, d1, d2, build.get("service"))

            # if FROM image is newer, this build should be re-built
            elif image_tag in overriding_builds:
                from_img = overriding_builds.get(image_tag, "")
                from_build = core_builds.get(from_img, {})

                # # This check should not be needed, added to prevent errors from mypy
                # if not from_build:  # pragma: no cover
                #     continue

                # Verify if template build exists
                if from_img not in dimages:  # pragma: no cover
                    log.warning(
                        "Missing template build for {} ({})\n{}",
                        from_build.get("services"),
                        from_img,
                    )

                from_timestamp = get_image_creation(from_img)
                # Verify if template build is obsolete or not
                d1, d2 = build_is_obsolete(from_timestamp, from_build)
                if d1 and d2:  # pragma: no cover
                    print_obsolete(from_img, d1, d2, from_build.get("service"))

                # from_timestamp = from_build["creation"]
                # build_timestamp = build["creation"]

                if from_timestamp > image_creation:
                    b = image_creation.strftime(DATE_FORMAT)
                    c = from_timestamp.strftime(DATE_FORMAT)
                    print_obsolete(image_tag, b, c, build.get("service"), from_img)

    templating = Templating()
    for f in Application.project_scaffold.fixed_files:
        if templating.file_changed(str(f)):
            log.warning("{f} changed, please execute rapydo upgrade --path {f}", f=f)

    log.info("Checks completed")


def print_obsolete(
    image: str, date1: str, date2: str, service: str, from_img: Optional[str] = None
) -> None:
    if from_img:
        log.warning(
            """Obsolete image {}
built on {} FROM {} that changed on {}
Update it with: rapydo --services {} build""",
            image,
            date1,
            from_img,
            date2,
            service,
        )
    else:
        log.warning(
            """Obsolete image {}
built on {} but changed on {}
Update it with: rapydo --services {} pull""",
            image,
            date1,
            date2,
            service,
        )


def build_is_obsolete(
    image_creation: datetime, build: Any
) -> Tuple[Optional[str], Optional[str]]:
    # compare dates between git and docker
    path = build.get("path")
    btempl = Application.gits.get("build-templates")
    vanilla = Application.gits.get("main")

    if btempl and btempl.working_dir and path.startswith(btempl.working_dir):
        git_repo = btempl
    elif vanilla and vanilla.working_dir and path.startswith(vanilla.working_dir):
        git_repo = vanilla
    else:  # pragma: no cover
        print_and_exit("Unable to find git repo {}", path)

    # build_timestamp = build["creation"].timestamp() if build["creation"] else 0.0

    build_timestamp = image_creation.timestamp() if image_creation else 0.0

    for f in Path(path).rglob("*"):
        if f.is_dir():  # pragma: no cover
            continue

        obsolete, build_ts, last_commit = git.check_file_younger_than(
            gitobj=git_repo, filename=f, timestamp=build_timestamp
        )

        if obsolete:
            log.info("File changed: {}", f)
            build_ts_f = datetime.fromtimestamp(build_ts).strftime(DATE_FORMAT)
            last_commit_str = last_commit.strftime(DATE_FORMAT)
            return build_ts_f, last_commit_str

    return None, None
