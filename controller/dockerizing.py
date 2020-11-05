import sys

import docker
import requests
from docker.errors import APIError

from controller import log


class Dock:
    def __init__(self):
        super().__init__()

        self.client = docker.from_env()

        if not self.is_daemon_alive():  # pragma: no cover
            log.critical("Docker daemon not reachable")
            sys.exit(1)

    def is_daemon_alive(self):

        try:
            return self.client.ping()
        # this is the case of docker daemon not started
        except requests.exceptions.ConnectionError:  # pragma: no cover
            return False
        # this is the case of docker daemon starting or not working properly
        except APIError:  # pragma: no cover
            return False

    def image_info(self, tag):
        obj = self.client.images.list(name=tag)
        try:
            return obj.pop().attrs
        except IndexError:
            return {}

    def image_attribute(self, tag, attribute="Created"):
        return self.image_info(tag).get(attribute, None)

    def images(self):
        images = []
        for obj in self.client.images.list():
            tags = obj.attrs.get("RepoTags")
            if tags is not None:
                images.extend(tags)
        return images
