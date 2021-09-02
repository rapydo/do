import json
from datetime import datetime
from typing import List, Optional, Tuple, cast

import typer
import urllib3

from controller import colors, log
from controller.app import Application
from controller.deploy.docker import Docker
from controller.utilities import system


@Application.app.command(help="Query the local registry")
def images(
    remove_images: List[str] = typer.Option(
        "",
        "--rm",
        "--remove",
        help="Remove the specified image(s)",
        show_default=False,
        autocompletion=Application.autocomplete_submodule,
    ),
) -> None:

    Application.get_controller().controller_init()

    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    # https://docs.docker.com/registry/spec/api/

    docker = Docker()

    docker.ping_registry()

    registry = docker.get_registry()
    host = f"https://{registry}"

    # Docker Registry API Reference
    # https://docs.docker.com/registry/spec/api/

    # Retrieve a sorted, json list of repositories available in the registry
    r = docker.send_registry_request(f"{host}/v2/_catalog")

    catalog = r.json()

    images: List[Tuple[str, str, str, int, Optional[datetime]]] = []
    for repository in catalog.get("repositories", {}):

        # Fetch the tags under the repository identified by <name>
        r = docker.send_registry_request(f"{host}/v2/{repository}/tags/list")

        for tag in r.json().get("tags", {}):

            # Fetch the manifest identified by name and reference
            r = docker.send_registry_request(f"{host}/v2/{repository}/manifests/{tag}")
            manifest = r.json()
            size = 0
            for layer in manifest.get("layers", []):
                size += layer.get("size", 0)

            headers = r.headers

            _id = cast(str, headers.get("Docker-Content-Digest", "N/A"))

            # Creation date is only available on schema version 1 :\
            r = docker.send_registry_request(
                f"{host}/v2/{repository}/manifests/{tag}", version="1"
            )
            manifest = r.json()
            layers = manifest.get("history", [])

            created: Optional[datetime] = None
            if len(layers) > 0:
                first_layer = json.loads(layers[0].get("v1Compatibility", {}))
                creation_date = first_layer.get("created", "N/A")
                if creation_date != "N/A":
                    creation_date = creation_date[0:19]
                    created = datetime.strptime(creation_date, "%Y-%m-%dT%H:%M:%S")

            images.append((_id, cast(str, repository), cast(str, tag), size, created))

    if not images:
        log.warning("This registry contains no images")
    else:

        log.info("This registry contains {} image(s):", len(images))
        print("")
        h0 = "ID"
        h1 = "Image"
        h2 = "Version"
        h3 = "Size"
        h4 = "Creation date"
        print(f"{h0:13}{h1:24}{h2:10}{h3:8}{h4}")
        images_to_be_removed: List[Tuple[str, str, str]] = []
        for img in images:

            digest = img[0]
            # to be replaced with removeprefix starting from py39
            if digest.startswith("sha256:"):
                digest = digest[7:]
            _id = digest[0:12]

            repository = img[1]
            tag = img[2]
            SIZE = system.bytes_to_str(img[3])
            d = img[4]

            to_be_removed = (
                _id in remove_images or f"{repository}:{tag}" in remove_images
            )
            creation_date = d.strftime("%Y-%m-%d %H:%M:%S") if d else "N/A"

            if to_be_removed:
                COLOR = colors.RED
                creation_date = "DELETING ..."
                images_to_be_removed.append((repository, digest, tag))
            else:
                COLOR = ""
            RESET = colors.RESET
            print(
                f"{COLOR}{_id:13}{repository:24}{tag:10}{SIZE:8}{creation_date}{RESET}"
            )

        if len(remove_images) != len(images_to_be_removed):
            log.error(
                "Some of the images that you specified are not found in this registry"
            )

        # DELETE /v2/<name>/manifests/<reference>
        for image in images_to_be_removed:
            repository = image[0]
            reference = image[1]  # digest without sha256:
            tag = image[2]
            # For deletes reference must be a digest or the delete will fail
            r = docker.send_registry_request(
                f"{host}/v2/{repository}/manifests/sha256:{reference}", method="DELETE"
            )

            log.info("Image {}:{} deleted from {}", repository, tag, host)
