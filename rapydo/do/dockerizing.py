# -*- coding: utf-8 -*-

import requests
import docker
from docker.errors import APIError as docker_errors
from rapydo.utils.logs import get_logger

log = get_logger(__name__)


class Dock(object):

    client = None

    def __init__(self):
        super(Dock, self).__init__()

        if not self.is_daemon_alive():
            log.critical_exit("Docker daemon not reachable")

    def is_daemon_alive(self):

        if self.client is None:
            self.client = docker.from_env()
        else:
            pass

        # from requests.packages.urllib3 import exceptions as reqex
        # try:
        #     self.client.containers.list()
        # except (FileNotFoundError, reqex.ProtocolError, ConnectionError):
        #     return False
        # else:
        #     return True

        try:
            return self.client.ping()
        # this is the case of docker daemon not started
        except requests.exceptions.ConnectionError:
            return False
        # this is the case of docker daemon starting or not working properly
        except docker_errors:
            return False

    def image_info(self, tag):
        obj = self.client.images.list(name=tag)
        try:
            return obj.pop().attrs
        except IndexError:
            return {}

    def image_attribute(self, tag, attribute='Created'):
        return self.image_info(tag).get(attribute, None)

    def images(self):
        images = []
        for obj in self.client.images.list():
            tags = obj.attrs.get('RepoTags')
            if tags is not None:
                images.extend(tags)
        # log.debug("Docker:%s" % images)
        return images

    # def some_docker():
    #     containers = client.containers.list()
    #     log.debug("Docker:%s" % containers)
