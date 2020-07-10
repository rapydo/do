import typer

from controller import log
from controller.app import Application
from controller.builds import locate_builds, remove_redundant_services
from controller.compose import Compose


@Application.app.command(help="Force building of one or more services docker images")
def build(
    core: bool = typer.Option(
        False,
        "--core",
        help="force build of all images including core builds",
        show_default=False,
    ),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="remove the build cache to force the complete rebuilding",
        show_default=False,
    ),
):
    Application.controller.controller_init()

    builds, template_builds, overriding_imgs = locate_builds(
        Application.data.base_services, Application.data.compose_config
    )

    if core:
        log.debug("Forcing rebuild of core builds")

        options = {
            "SERVICE": remove_redundant_services(
                Application.data.services, template_builds
            ),
            "--no-cache": force,
            "--force-rm": True,
            "--pull": True,
            "--parallel": True,
        }
        dc = Compose(files=Application.data.base_files)
        dc.command("build", options)
        log.info("Core images built")

    # Only build images defined at project level, overriding core images
    # Core images should only be pulled or built by specificing --core
    custom_services = []
    for img, build in builds.items():
        if img in overriding_imgs:
            custom_services.extend(build.get("services", []))
    build_services = remove_redundant_services(custom_services, builds)

    # Remove services not selected at project level, i.e. restricted by --services
    build_services = [i for i in build_services if i in Application.data.services]
    if not build_services:
        log.info("No custom images to build")
    else:
        options = {
            "SERVICE": build_services,
            "--no-cache": force,
            "--force-rm": True,
            "--pull": not core,
            "--parallel": True,
        }
        dc = Compose(files=Application.data.files)
        dc.command("build", options)

        log.info("Custom images built")
