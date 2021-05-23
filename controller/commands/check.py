from datetime import datetime
from pathlib import Path
from typing import List

import typer
from python_on_whales import docker
from python_on_whales.utils import DockerException

from controller import gitter, log
from controller.app import Application
from controller.builds import locate_builds
from controller.swarm import Swarm
from controller.templating import Templating

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

    # Set as first operation to quickly exit in case of docker issues
    try:
        dimages = [img.repo_tags[0] for img in docker.images() if img.repo_tags]
    except DockerException as e:  # pragma: no cover
        Application.exit(e)

    Application.get_controller().controller_init()

    swarm = Swarm()
    if not swarm.get_token():
        Application.exit("Swarm is not initialized, please execute rapydo init")
    log.debug("Swarm is correctly initialized")

    if no_git:
        log.info("Skipping git checks")
    else:
        log.info("Checking git (skip with --no-git)")
        Application.git_checks(ignore_submodules)

    if no_builds:
        log.info("Skipping builds checks")
    else:
        log.info("Checking builds (skip with --no-builds)")

        # Compare builds depending on templates (slow operation!)
        builds, template_builds, overriding_imgs = locate_builds(
            Application.data.base_services, Application.data.compose_config
        )

        for image_tag, build in builds.items():

            if image_tag not in dimages:
                continue

            if not any(
                x in Application.data.active_services for x in build["services"]
            ):  # pragma: no cover
                continue

            # Check if some recent commit modified the Dockerfile
            obsolete, d1, d2 = build_is_obsolete(build, Application.gits)
            if obsolete:
                print_obsolete(image_tag, d1, d2, build.get("service"))

            # if FROM image is newer, this build should be re-built
            elif image_tag in overriding_imgs:
                from_img = overriding_imgs.get(image_tag)
                from_build = template_builds.get(from_img)

                # Verify if template build exists
                if from_img not in dimages:  # pragma: no cover

                    # This is no longer an errore because custom images may be pulled
                    # from the docker hub. In that case template images are not required
                    # Application.exit(
                    #     "Missing template build for {} ({})\n{}",
                    #     from_build["services"],
                    #     from_img,
                    #     "Suggestion: execute the pull command",
                    # )
                    log.warning(
                        "Missing template build for {} ({})\n{}",
                        from_build["services"],
                        from_img,
                    )

                # Verify if template build is obsolete or not
                obsolete, d1, d2 = build_is_obsolete(from_build, Application.gits)
                if obsolete:  # pragma: no cover
                    print_obsolete(from_img, d1, d2, from_build.get("service"))

                from_timestamp = from_build["creation"]
                build_timestamp = build["creation"]

                if from_timestamp > build_timestamp:
                    b = build_timestamp.strftime(DATE_FORMAT)
                    c = from_timestamp.strftime(DATE_FORMAT)
                    print_obsolete(image_tag, b, c, build.get("service"), from_img)

    templating = Templating()
    for f in Application.project_scaffold.fixed_files:
        if templating.file_changed(str(f)):
            log.warning("{f} changed, please execute rapydo upgrade --path {f}", f=f)

    log.info("Checks completed")


def print_obsolete(image, date1, date2, service, from_img=None):
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


def build_is_obsolete(build, gits):
    # compare dates between git and docker
    path = build.get("path")
    build_templates = gits.get("build-templates")
    vanilla = gits.get("main")

    if path.startswith(build_templates.working_dir):
        git_repo = build_templates
    elif path.startswith(vanilla.working_dir):
        git_repo = vanilla
    else:  # pragma: no cover
        Application.exit("Unable to find git repo {}", path)

    build_timestamp = build["creation"].timestamp() if build["creation"] else 0.0

    for f in Path(path).rglob("*"):
        if f.is_dir():  # pragma: no cover
            continue

        obsolete, build_ts, last_commit = gitter.check_file_younger_than(
            gitobj=git_repo, filename=f, timestamp=build_timestamp
        )

        if obsolete:
            log.info("File changed: {}", f)
            build_ts_f = datetime.fromtimestamp(build_ts).strftime(DATE_FORMAT)
            last_commit_str = last_commit.strftime(DATE_FORMAT)
            return True, build_ts_f, last_commit_str

    return False, 0, 0
