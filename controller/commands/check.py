# -*- coding: utf-8 -*-
import os
import dateutil.parser
from datetime import datetime
from controller.dockerizing import Dock
from controller.builds import locate_builds
from controller import gitter
from controller import log

DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def print_obsolete(image, date1, date2, service, from_img=None):
    if from_img:
        log.warning(
            """Obsolete image {}
built on {} FROM {} that changed on {}
Update it with: rapydo --services {} pull""",
            image,
            date1,
            from_img,
            date2,
            service
        )
    else:
        log.warning(
            """Obsolete image {}
built on {} but changed on {}
Update it with: rapydo --services {} pull""",
            image,
            date1,
            date2,
            service
        )


def get_build_timestamp(build, as_date=False):

    # timestamp is like: 2017-09-22T07:10:35.822772835Z
    timestamp = build.get('timestamp')

    if timestamp is None:
        log.warning("Received a null timestamp, defaulting to zero")
        timestamp = 0

    d = dateutil.parser.parse(timestamp)
    if as_date:
        return d

    return d.timestamp()


def build_is_obsolete(build, gits):
    # compare dates between git and docker
    path = build.get('path')
    build_templates = gits.get('build-templates')
    vanilla = gits.get('main')

    if path.startswith(build_templates.working_dir):
        git_repo = build_templates
    elif path.startswith(vanilla.working_dir):
        git_repo = vanilla
    else:
        log.exit("Unable to find git repo {}", path)

    build_timestamp = get_build_timestamp(build)

    files = os.listdir(path)
    for f in files:
        local_file = os.path.join(path, f)

        obsolete, build_ts, last_commit = gitter.check_file_younger_than(
            gitobj=git_repo, filename=local_file, timestamp=build_timestamp
        )

        if obsolete:
            log.info("File changed: {}", f)
            build_ts = datetime.fromtimestamp(build_ts).strftime(DATE_FORMAT)
            last_commit = last_commit.strftime(DATE_FORMAT)
            return True, build_ts, last_commit

    return False, 0, 0


def __call__(args, base_services, compose_config, active_services, gits, **kwargs):

    if args.get('no_builds', False):
        log.info("Skipping builds checks")
    else:
        log.info("Checking builds (skip with --no-builds)")

        # Compare builds depending on templates (slow operation!)
        builds, template_builds, overriding_imgs = locate_builds(
            base_services, compose_config
        )

        if len(builds) == 0:
            log.debug("No build to be verified")
        else:

            dimages = Dock().images()

            for image_tag, build in builds.items():

                if image_tag not in dimages:
                    # Missing images will be created at startup
                    log.info("Image {} is missing", image_tag)
                    continue

                if not any(x in active_services for x in build['services']):
                    log.verbose(
                        "Checks skipped: template {} not enabled (service list = {})",
                        image_tag,
                        build['services'],
                    )
                    continue

                # Check if some recent commit modified the Dockerfile
                obsolete, d1, d2 = build_is_obsolete(build, gits)
                if obsolete:
                    print_obsolete(image_tag, d1, d2, build.get('service'))

                # if FROM image is newer, this build should be re-built
                elif image_tag in overriding_imgs:
                    from_img = overriding_imgs.get(image_tag)
                    from_build = template_builds.get(from_img)

                    # Verify if template build exists
                    if from_img not in dimages:

                        log.exit(
                            "Missing template build for {} ({})\n{}",
                            from_build['services'],
                            from_img,
                            "Suggestion: execute the pull command"
                        )

                    # Verify if template build is obsolete or not
                    obsolete, d1, d2 = build_is_obsolete(from_build, gits)
                    if obsolete:
                        print_obsolete(from_img, d1, d2, from_build.get('service'))

                    from_timestamp = get_build_timestamp(from_build, as_date=True)
                    build_timestamp = get_build_timestamp(build, as_date=True)

                    if from_timestamp > build_timestamp:
                        b = build_timestamp.strftime(DATE_FORMAT)
                        c = from_timestamp.strftime(DATE_FORMAT)
                        print_obsolete(image_tag, b, c, build.get('service'), from_img)

    log.info("Checks completed")
