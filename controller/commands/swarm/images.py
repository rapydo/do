import json
from datetime import datetime
from typing import List, Optional, Tuple, cast

import urllib3

from controller import log
from controller.app import Application
from controller.deploy.docker import Docker


@Application.app.command(help="Query the local registry")
def images() -> None:
    Application.get_controller().controller_init()

    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    # https://docs.docker.com/registry/spec/api/

    docker = Docker()

    docker.ping_registry()

    registry = docker.get_registry()
    host = f"https://{registry}"
    r = docker.send_registry_request(f"{host}/v2/_catalog")

    catalog = r.json()

    images: List[Tuple[str, str, str, Optional[datetime]]] = []
    for repository in catalog.get("repositories", {}):
        r = docker.send_registry_request(f"{host}/v2/{repository}/tags/list")

        for tag in r.json().get("tags", {}):

            r = docker.send_registry_request(f"{host}/v2/{repository}/manifests/{tag}")
            manifest = r.json()
            headers = r.headers
            _id = cast(str, headers.get("Docker-Content-Digest", "N/A"))

            layers = manifest.get("history", [])

            created: Optional[datetime] = None
            if len(layers) > 0:
                first_layer = json.loads(layers[0].get("v1Compatibility", {}))
                creation_date = first_layer.get("created", "N/A")
                if creation_date != "N/A":
                    creation_date = creation_date[0:19]
                    created = datetime.strptime(creation_date, "%Y-%m-%dT%H:%M:%S")

            images.append((_id, cast(str, repository), cast(str, tag), created))

    if not images:
        log.warning("This registry contains no images")
    else:

        log.info("This registry contains {} image(s):", len(images))
        print("")
        h0 = "ID"
        h1 = "Image"
        h2 = "Version"
        h3 = "Creation date"
        print(f"{h0:13}{h1:24}{h2:10}{h3}")
        for img in images:
            _id = img[0]
            # to be replaced with removeprefix starting from py39
            if _id.startswith("sha256:"):
                _id = _id[7:]
                _id = _id[0:12]

            repository = img[1]
            tag = img[2]
            d = img[3]
            creation_date = d.strftime("%Y-%m-%d %H:%M:%S") if d else "N/A"
            print(f"{_id:13}{repository:24}{tag:10}{creation_date}")
