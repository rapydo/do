import typer

from controller import log
from controller.app import Application, Configuration
from controller.builds import locate_builds, remove_redundant_services
from controller.compose import Compose


@Application.app.command(help="Force building of one or more services docker images")
def build(
    core: bool = typer.Option(
        False,
        "--core",
        help="force the build of all images including core builds",
        show_default=False,
    ),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="remove the cache to force a rebuilding",
        show_default=False,
    ),
    yes: bool = typer.Option(
        False,
        "--yes",
        help="assume 'yes' as answer to all prompts and run non-interactively",
        show_default=False,
    ),
) -> bool:
    Application.get_controller().controller_init()

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
    service2img = {}
    img2services = {}
    for img, build in builds.items():
        if img in overriding_imgs:
            services = build.get("services", [])
            custom_services.extend(build.get("services", []))

            # These will be used to verify running images
            img2services[img] = services
            for service in services:
                service2img[service] = img

    # Remove services not selected at project level, i.e. restricted by --service
    build_services = [i for i in custom_services if i in Application.data.services]

    build_services = remove_redundant_services(build_services, builds)

    if not build_services:
        log.info("No custom images to build")
        return False

    options = {
        "SERVICE": build_services,
        "--no-cache": force,
        "--force-rm": True,
        "--pull": not core,
        "--parallel": True,
    }
    dc = Compose(files=Application.data.files)

    if not yes:
        running_containers = dc.get_running_containers(Configuration.project)

        # Expand the list of build services with all services using the same image
        # and verify if any of them is running
        for s in build_services:
            # This the image that will be built for this service:
            img = service2img.get(s)
            # Get the list of services using the same image (img2services.get(img))
            # and check if any of these services is running
            running = [
                i for i in img2services.get(img, "N/A") if i in running_containers
            ]

            if not running:
                continue

            log.warning(
                "You asked to build {} but the following containers are running: {}",
                img,
                ", ".join(running),
            )

            print("If you continue, the current build will be kept with a <none> tag\n")

            while True:
                response = typer.prompt("Do you want to continue? y/n")
                if response.lower() in ["n", "no"]:
                    Application.exit("Build aborted")

                if response.lower() in ["y", "yes"]:
                    break

                log.warning("Unknown response {}, respond yes or no", response)
                # In any other case, as again

    dc.command("build", options)

    log.info("Custom images built")
    return True
