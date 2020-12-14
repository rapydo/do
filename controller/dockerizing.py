import sys
from typing import List

import docker
import requests
from docker.errors import APIError

from controller import log


class Dock:
    def __init__(self):
        super().__init__()

        self.client = docker.from_env()
        try:
            self.client.ping()
        # this is the case of docker daemon not started
        except requests.exceptions.ConnectionError:  # pragma: no cover
            log.critical("Docker daemon not reachable")
            sys.exit(1)
        # this is the case of docker daemon still starting or not working properly
        except APIError:  # pragma: no cover
            log.critical("Docker daemon not reachable")
            sys.exit(1)

    def image_info(self, tag):
        obj = self.client.images.list(name=tag)
        try:
            return obj.pop().attrs
        except IndexError:
            return {}

    def images(self) -> List[str]:
        images = []
        for obj in self.client.images.list():
            tags = obj.attrs.get("RepoTags")
            if tags is not None:
                images.extend(tags)
        return images
