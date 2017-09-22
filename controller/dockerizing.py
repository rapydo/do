# -*- coding: utf-8 -*-

import io
import tarfile
import requests
import docker
from docker.errors import APIError as docker_errors
from utilities.logs import get_logger

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

    def get_container(self, substring, only_prefix=None):

        containers = self.client.containers.list()
        log.very_verbose("Docker:%s" % containers)

        for container in containers:
            name = container.attrs.get('Name')
            if only_prefix is not None and only_prefix not in name:
                continue
            if substring in name:
                return container

        return None

    def copy_file(self, service_name, containers_prefix, mitt, dest):

        container = self.get_container(
            '_%s_1' % service_name, only_prefix=containers_prefix)
        if container is None:
            log.exit("Are docker containers running?")

        tar_content = self.get_tar_content(container, mitt)
        real_content = self.recover_tar_stream(tar_content, mitt)

        with open(dest, 'w') as handler:
            handler.write(real_content)

    def get_tar_content(self, container, path):
        # http://docker-py.readthedocs.io/en/1.5.0/api/#get_archive

        try:
            # content, stats = self.client.api.get_archive(
            content, _ = self.client.api.get_archive(
                container=container.attrs,
                path=path,
            )
        except docker.errors.NotFound:
            log.exit("Path %s not found in container %s" % (path, container))

        return content

    def recover_tar_stream(self, tarstream, filepath):

        tar = tarfile.open(fileobj=io.BytesIO(tarstream.read()))

        members = tar.getmembers().copy()
        tarinfo = members.pop()
        current_file = tarinfo.get_info().get('name')
        if not filepath.endswith(current_file):
            log.exit("Something went wrong")

        efo = tar.extractfile(current_file)
        efo.seek(0)
        return efo.read().decode()
