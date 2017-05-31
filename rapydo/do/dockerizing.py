# -*- coding: utf-8 -*-

import docker
from rapydo.utils.logs import get_logger

log = get_logger(__name__)


class Dock(object):

    def __init__(self):
        super(Dock, self).__init__()
        self.client = docker.from_env()

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
            for tag in obj.attrs.get('RepoTags', []):
                images.append(tag)
        # log.debug("Docker:%s" % images)
        return images

    # def some_docker():
    #     containers = client.containers.list()
    #     log.debug("Docker:%s" % containers)
