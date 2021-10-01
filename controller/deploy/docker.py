import shlex
import socket
from typing import List, Optional, cast

import requests
import urllib3
from python_on_whales import DockerClient
from python_on_whales.exceptions import NoSuchService
from python_on_whales.utils import DockerException
from requests.auth import HTTPBasicAuth
from requests.models import Response

from controller import RED, SWARM_MODE, print_and_exit
from controller.app import Application, Configuration


class Docker:
    def __init__(self) -> None:

        self.client = DockerClient(host=self.get_engine())

    @classmethod
    def get_engine(cls) -> Optional[str]:
        if not Configuration.remote_engine:
            return None

        if not cls.validate_remote_engine(Configuration.remote_engine):
            print_and_exit(
                "Invalid remote host {}, expected user@ip-or-hostname",
                Configuration.remote_engine,
            )

        return f"ssh://{Configuration.remote_engine}"

    @staticmethod
    def validate_remote_engine(host: str) -> bool:
        if "@" not in host:
            return False
        # TODO: host should be validated as:
        # user @ ip | host
        return True

    @staticmethod
    def get_registry() -> str:
        registry_host = Application.env["REGISTRY_HOST"]
        registry_port = Application.env["REGISTRY_PORT"]

        return f"{registry_host}:{registry_port}"

    def ping_registry(self, do_exit: bool = True) -> bool:

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
                    self.get_registry(),
                    command=RED("rapydo run registry"),
                )

            return False

    @staticmethod
    def send_registry_request(
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

    def verify_registry_image(self, image: str) -> bool:

        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        registry = self.get_registry()
        host = f"https://{registry}"
        repository, tag = image.split(":")
        r = self.send_registry_request(
            f"{host}/v2/{repository}/manifests/{tag}", check_status=False
        )

        return r.status_code == 200

    def login(self) -> None:

        registry = self.get_registry()
        try:
            self.client.login(
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

    @staticmethod
    def split_command(command: Optional[str]) -> List[str]:
        # Needed because:
        # Passing None for 's' to shlex.split() is deprecated
        if command is None:
            return []

        return shlex.split(command)

    @classmethod
    def get_service(cls, service: str) -> str:
        if not SWARM_MODE:
            return f"{Configuration.project}_{service}"
        return f"{Configuration.project}_{service}"

    def get_container(self, service: str, slot: int) -> Optional[str]:

        service_name = self.get_service(service)

        if not SWARM_MODE:
            c = f"{service_name}-{slot}"
            if self.client.container.exists(c):
                return c
            return None

        try:
            for task in self.client.service.ps(service_name):
                if task.slot != slot:
                    continue

                return f"{service_name}.{slot}.{task.id}"
        except NoSuchService:
            return None

        return None

    def exec_command(
        self,
        container: str,
        user: Optional[str] = None,
        command: str = None,
        tty: bool = True,
    ) -> None:
        print("")
        print(
            self.client.container.execute(
                container,
                user=user,
                command=self.split_command(command),
                interactive=tty,
                tty=tty,
                detach=False,
            )
        )
