"""
Verify if the current project is compliant to RAPyDo specs
"""
import re
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple

import typer

from controller import RED, log, print_and_exit
from controller.app import Application, Configuration
from controller.commands.password import get_expired_passwords
from controller.deploy.builds import (
    TemplateInfo,
    find_templates_build,
    find_templates_override,
    get_image_creation,
)
from controller.deploy.docker import Docker
from controller.packages import BUILDX_VERSION, COMPOSE_VERSION
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
        [],
        "--ignore-submodule",
        "-i",
        help="Ignore submodule",
        show_default=False,
        shell_complete=Application.autocomplete_submodule,
    ),
) -> None:

    Application.print_command(
        Application.serialize_parameter("--no-git", no_git, IF=no_git),
        Application.serialize_parameter("--no-builds", no_builds, IF=no_builds),
        Application.serialize_parameter("--ignore-submodule", ignore_submodules),
    )
    Application.get_controller().controller_init()

    docker = Docker()
    if Configuration.swarm_mode:
        log.debug("Swarm is correctly initialized")

        docker.swarm.check_resources()

    if no_git:
        log.info("Skipping git checks")
    else:
        log.info("Checking git (skip with --no-git)")
        Application.git_checks(ignore_submodules)

    if no_builds:
        log.info("Skipping builds checks")
    else:
        log.info("Checking builds (skip with --no-builds)")

        dimages: List[str] = []

        for img in docker.client.images():
            if img.repo_tags:
                for i in img.repo_tags:
                    dimages.append(i)

        all_builds = find_templates_build(Application.data.compose_config)
        core_builds = find_templates_build(Application.data.base_services)
        overriding_builds = find_templates_override(
            Application.data.compose_config, core_builds
        )

        for image_tag, build in all_builds.items():

            services = build["services"]
            if not any(x in Application.data.active_services for x in services):
                continue

            if image_tag not in dimages:
                if image_tag in core_builds:
                    log.warning(
                        "Missing {} image, execute {command}",
                        image_tag,
                        command=RED("rapydo pull"),
                    )
                else:
                    log.warning(
                        "Missing {} image, execute {command}",
                        image_tag,
                        command=RED("rapydo build"),
                    )
                continue

            image_creation = get_image_creation(image_tag)
            # Check if some recent commit modified the Dockerfile

            d1, d2 = build_is_obsolete(image_creation, build.get("path"))
            if d1 and d2:
                tmp_from_image = overriding_builds.get(image_tag)
                # This is the case of a build not overriding a core image,
                # e.g nifi or geoserver. In that case from_image is faked to image_tag
                # just to make print_obsolete to print 'build' instead of 'pull'
                if not tmp_from_image and image_tag not in core_builds:
                    tmp_from_image = image_tag

                print_obsolete(image_tag, d1, d2, build.get("service"), tmp_from_image)

            # if FROM image is newer, this build should be re-built
            elif image_tag in overriding_builds:
                from_img = overriding_builds.get(image_tag, "")
                from_build: Optional[TemplateInfo] = core_builds.get(from_img)

                if not from_build:  # pragma: no cover
                    log.critical("Malformed {} image, from build is missing", image_tag)
                    continue

                # Verify if template build exists
                if from_img not in dimages:  # pragma: no cover
                    log.warning(
                        "Missing template build for {} ({})\n{}",
                        from_build.get("services"),
                        from_img,
                    )

                from_timestamp = get_image_creation(from_img)
                # Verify if template build is obsolete or not

                d1, d2 = build_is_obsolete(from_timestamp, from_build.get("path"))
                if d1 and d2:  # pragma: no cover
                    print_obsolete(from_img, d1, d2, from_build.get("service"))

                if from_timestamp > image_creation:
                    b = image_creation.strftime(DATE_FORMAT)
                    c = from_timestamp.strftime(DATE_FORMAT)
                    print_obsolete(image_tag, b, c, build.get("service"), from_img)

    templating = Templating()
    for filename in Application.project_scaffold.fixed_files:
        if templating.file_changed(str(filename)):
            log.warning(
                "{} changed, please execute {command}",
                filename,
                command=RED(f"rapydo upgrade --path {filename}"),
            )

    compose_version = "Unknown"
    buildx_version = "Unknown"
    m = re.search(
        r"^Docker Compose version (v[0-9]+\.[0-9]+\.[0-9]+)$",
        docker.client.compose.version(),
    )
    if m:
        compose_version = m.group(1)

    m = re.search(
        r"^github.com/docker/buildx (v[0-9]+\.[0-9]+\.[0-9]+) .*$",
        docker.client.buildx.version(),
    )
    if m:
        buildx_version = m.group(1)

    if compose_version == COMPOSE_VERSION:
        log.info("Compose is installed with version {}", COMPOSE_VERSION)
    else:  # pragma: no cover
        cmd = RED("rapydo install compose")
        fix_hint = f"You can update it with {cmd}"
        log.warning(
            "Compose is installed with version {}, expected version is {}.\n{}",
            compose_version,
            COMPOSE_VERSION,
            fix_hint,
        )

    if buildx_version == BUILDX_VERSION:
        log.info("Buildx is installed with version {}", BUILDX_VERSION)
    else:  # pragma: no cover
        cmd = RED("rapydo install buildx")
        fix_hint = f"You can update it with {cmd}"
        log.warning(
            "Buildx is installed with version {}, expected version is {}.\n{}",
            buildx_version,
            BUILDX_VERSION,
            fix_hint,
        )

    for expired_passwords in get_expired_passwords():
        log.warning(
            "{} is expired on {}",
            expired_passwords[0],
            expired_passwords[1].strftime("%Y-%m-%d"),
        )

    log.info("Checks completed")


def print_obsolete(
    image: str,
    date1: str,
    date2: str,
    service: Optional[str],
    from_img: Optional[str] = None,
) -> None:

    if service:
        if from_img:
            log.warning(
                """Obsolete image {}: built on {} FROM {} that changed on {}
Update it with: {command}""",
                image,
                date1,
                from_img,
                date2,
                command=RED(f"rapydo build {service}"),
            )
        else:
            log.warning(
                """Obsolete image {}: built on {} but changed on {}
Update it with: {command}""",
                image,
                date1,
                date2,
                command=RED(f"rapydo pull {service}"),
            )


def is_relative_to(path: Path, rel: str) -> bool:
    # This works from py39
    try:
        return path.is_relative_to(rel)
    # py38 compatibility fix
    except Exception:
        try:
            path.relative_to(rel)
            return True
        except ValueError:
            return False


def build_is_obsolete(
    image_creation: datetime, path: Optional[Path]
) -> Tuple[Optional[str], Optional[str]]:

    if not path:  # pragma: no cover
        return None, None

    # compare dates between git and docker
    btempl = Application.gits.get("build-templates")
    vanilla = Application.gits.get("main")

    if btempl and btempl.working_dir and is_relative_to(path, str(btempl.working_dir)):
        git_repo = btempl
    elif (
        vanilla
        and vanilla.working_dir
        and is_relative_to(path, str(vanilla.working_dir))
    ):
        git_repo = vanilla
    else:  # pragma: no cover
        print_and_exit("Unable to find git repo {}", path)

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
