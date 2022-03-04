import socket
from typing import cast

import requests
import urllib3
from python_on_whales.utils import DockerException
from requests.auth import HTTPBasicAuth
from requests.models import Response

from controller import RED, print_and_exit
from controller.app import Application
from controller.deploy.docker import Docker


class Registry:
    def __init__(self, docker: Docker):
        self.docker = docker.client

    @staticmethod
    def get_host() -> str:
        registry_host = Application.env["REGISTRY_HOST"]
        registry_port = Application.env["REGISTRY_PORT"]

        return f"{registry_host}:{registry_port}"

    def ping(self, do_exit: bool = True) -> bool:

        registry_host = Application.env["REGISTRY_HOST"]
        registry_port = int(Application.env.get("REGISTRY_PORT", "5000") or "5000")

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(1)
            try:
                result = sock.connect_ex((registry_host, registry_port))
            except socket.gaierror:
                # The error is not important, let's use a generic -1
                # result = errno.ESRCH
                result = -1

            if result == 0:
                return True

            if do_exit:
                print_and_exit(
                    "Registry {} not reachable. You can start it with {command}",
                    self.get_host(),
                    command=RED("rapydo run registry"),
                )

            return False

    @staticmethod
    def send_request(
        url: str, check_status: bool = True, method: str = "GET", version: str = "2"
    ) -> Response:

        if version == "2":
            headers = {"Accept": "application/vnd.docker.distribution.manifest.v2+json"}
        else:
            headers = {}
        if method == "DELETE":
            expected_status = 202
            method_ref = requests.delete

        else:
            expected_status = 200
            method_ref = requests.get

        r = method_ref(
            url,
            verify=False,
            auth=HTTPBasicAuth(
                Application.env["REGISTRY_USERNAME"],
                Application.env["REGISTRY_PASSWORD"],
            ),
            headers=headers,
        )

        if check_status and r.status_code != expected_status:
            print_and_exit(
                "The registry responded with an unexpected status {} ({} {})",
                str(r.status_code),
                method,
                url,
            )

        return r

    def verify_image(self, image: str) -> bool:

        urllib3.disable_warnings(  # type: ignore
            urllib3.exceptions.InsecureRequestWarning
        )
        registry = self.get_host()
        host = f"https://{registry}"
        repository, tag = image.split(":")
        r = self.send_request(
            f"{host}/v2/{repository}/manifests/{tag}", check_status=False
        )

        if r.status_code == 401:  # pragma: no cover
            print_and_exit("Access denied to {} registry", host)

        return r.status_code == 200

    def login(self) -> None:

        registry = self.get_host()
        try:
            self.docker.login(
                server=registry,
                username=cast(str, Application.env["REGISTRY_USERNAME"]),
                password=cast(str, Application.env["REGISTRY_PASSWORD"]),
            )
        except DockerException as e:
            if "docker login --username" in str(e):

                settings = f"""
{{
  "insecure-registries" : ["{registry}"]
}}
"""

                print_and_exit(
                    "Your registry TLS certificate is untrusted.\n\nYou should add the "
                    "following setting into your /etc/docker/daemon.json\n{}\n"
                    "and then restart the docker daemon\n",
                    settings,
                )

            raise e
