# -*- coding: utf-8 -*-

import docker
# from rapydo.utils.logs import get_logger

# log = get_logger(__name__)


class Dock(object):

    def __init__(self):
        super(Dock, self).__init__()
        self.client = docker.from_env()

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
