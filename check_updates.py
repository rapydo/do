import distutils.core
import json
import os
import re
import sys
import time
from distutils.version import LooseVersion
from glob import glob
from pathlib import Path
from typing import Any, Dict, List, Optional

import click
import requests
import yaml
from bs4 import BeautifulSoup
from loguru import logger as log

Dependencies = Dict[str, Dict[str, List[str]]]
# change current dir to the folder containing this script
# this way the script will be allowed to access all required files
# by providing relative links
os.chdir(os.path.dirname(__file__))

# https://raw.githubusercontent.com/antirez/redis/6.0/00-RELEASENOTES
changelogs = {
    # ## NPM
    "@ng-bootstrap/ng-bootstrap": "https://github.com/ng-bootstrap/ng-bootstrap/blob/master/CHANGELOG.md",
    "ngx-spinner": "https://github.com/Napster2210/ngx-spinner/releases",
    "ngx-formly": "https://github.com/ngx-formly/ngx-formly/releases",
    "ajv": "https://github.com/ajv-validator/ajv/releases",
    "dotenv": "https://github.com/motdotla/dotenv/blob/HEAD/CHANGELOG.md",
    "ngx-uploadx": "https://github.com/kukhariev/ngx-uploadx/releases",
    "karma": "https://github.com/karma-runner/karma/blob/master/CHANGELOG.md",
    # ## PYPI
    "schemathesis": "https://schemathesis.readthedocs.io/en/stable/changelog.html",
    # ## DockerHub
}


skip_versions = {"flower": "0.9.7", "typescript": "4.3.2"}


# This Any is required because yaml.load_all is untyped
def load_yaml_file(filepath: Path) -> Any:

    log.debug("Reading file {}", filepath)

    if filepath is None or not filepath.exists():
        log.warning("Failed to read YAML file {}: File does not exist", filepath)
        return {}

    with open(filepath) as fh:
        try:
            loader = yaml.load_all(fh, yaml.loader.Loader)

            docs = list(loader)

            if not docs:
                log.critical("YAML file is empty: {}", filepath)
                sys.exit(1)

            return docs[0]

        except BaseException as e:

            log.warning("Failed to read YAML file [{}]: {}", filepath, e)
            return {}


def check_updates(
    category: str, lib: str, npm_timeout: int, dockerhub_timeout: int
) -> None:

    if category == "pip":
        if "==" in lib:
            tokens = lib.split("==")
        elif ">=" in lib:
            return
            # tokens = lib.split(">=")
        else:
            log.critical("Invalid lib format: {}", lib)
            sys.exit(1)

        if "[" in tokens[0]:
            tokens[0] = tokens[0].split("[")[0]

        # url = f"https://pypi.org/project/{tokens[0]}/{tokens[1]}"
        url = f"https://pypi.org/project/{tokens[0]}"
        latest = parse_pypi(url, tokens[0])

        if tokens[0] in skip_versions and latest == skip_versions.get(tokens[0]):
            print(f"# Skipping version {latest} for {tokens[0]}")
            print("")
            return

        if latest != tokens[1]:
            print(f"# [{tokens[0]}]: {tokens[1]} -> {latest}")
            print(url)
            if changelog := changelogs.get(tokens[0]):
                print(changelog)
            print("")

    elif category in ["compose", "Dockerfile"]:
        tokens = lib.split(":")
        # remove any additinal word from the version from example in case of:
        # FROM imgname: imgversion AS myname => imgversion AS myname => imgversion
        tokens[1] = tokens[1].split(" ")[0]

        if "/" in tokens[0]:
            url = f"https://hub.docker.com/r/{tokens[0]}?tab=tags"
        else:
            url = f"https://hub.docker.com/_/{tokens[0]}?tab=tags"

        latest = parse_dockerhub(tokens[0], dockerhub_timeout)

        if tokens[0] in skip_versions and latest == skip_versions.get(tokens[0]):
            print(f"# Skipping version {latest} for {tokens[0]}")
            print("")
            return

        if latest != tokens[1]:
            print(f"# [{tokens[0]}]: {tokens[1]} -> {latest}")
            print(url)
            if changelog := changelogs.get(tokens[0]):
                print(changelog)
            print("")
    elif category in ["package.json", "dev-package.json", "npm"]:
        lib = lib.strip()
        if ":" in lib:
            tokens = lib.split(":")
        elif "@" in lib:
            if lib[0] == "@":
                tokens = lib[1:].split("@")
                tokens[0] = f"@{tokens[0]}"
            else:
                tokens = lib.split("@")
        else:
            tokens = [lib, ""]

        url = f"https://www.npmjs.com/package/{tokens[0]}"
        latest = parse_npm(url, tokens[0], npm_timeout, tokens[1])

        if tokens[0] in skip_versions and latest == skip_versions.get(tokens[0]):
            print(f"# Skipping version {latest} for {tokens[0]}")
            print("")
            return

        if latest != tokens[1]:
            print(f"# [{tokens[0]}]: {tokens[1]} -> {latest}")
            print(url)
            if changelog := changelogs.get(tokens[0]):
                print(changelog)
            print("")

    else:
        log.critical("{}: {}", category, lib)


def parse_npm(url: str, lib: str, sleep_time: int, current_version: str) -> str:

    # This is to prevent duplicated checks on libraries beloging the same family
    if lib in [
        "@angular/compiler",
        "@angular/core",
        "@angular/forms",
        "@angular/platform-browser",
        "@angular/platform-browser-dynamic",
        "@angular/router",
        "@angular/animations",
        "@angular/localize",
        "@angular/language-service",
        "@angular/platform-server",
        "@angular/compiler-cli",
    ]:

        return current_version

    time.sleep(sleep_time)

    page = requests.get(url)
    soup = BeautifulSoup(page.content, "html5lib")
    span = soup.find("span", attrs={"title": lib})

    if span is None:
        log.error("Span not found for: {} ({})", lib, url)
        return "unknown"

    spans = span.parent.parent.findChildren("span", recursive=False)
    return spans[0].text.split("\xa0")[0]  # type: ignore


def parse_pypi(url: str, lib: str) -> str:

    page = requests.get(url)
    soup = BeautifulSoup(page.content, "html5lib")
    span = soup.find("h1", attrs={"class": "package-header__name"})

    if span is None:
        log.critical("Cannot find pip-command for {}", lib)

    return span.text.strip().replace(f"{lib} ", "").strip()  # type: ignore


# Sem ver with 3 tokens (like... mostly everything!)
SEMVER3 = r"^[0-9]+\.[0-9]+\.[0-9]+$"
# Sem ver with 2 tokens (like Ubuntu 20.04)
SEMVER2 = r"^[0-9]+\.[0-9]+$"


def get_latest_version(
    tags: List[str],
    regexp: str = SEMVER3,
    suffix: str = "",
    ignores: Optional[List[str]] = None,
) -> str:

    if ignores is None:
        ignores = []

    latest = "0.0.0"
    for t in tags:

        clean_t = t.replace(suffix, "")

        if clean_t in ignores:
            continue

        if not re.match(regexp, clean_t):
            continue

        clean_latest = latest.replace(suffix, "")
        if LooseVersion(clean_t) > LooseVersion(clean_latest):
            latest = t

    return latest


def parse_dockerhub(lib: str, sleep_time: int) -> str:

    if lib == "stilliard/pure-ftpd":
        return "stretch-latest"

    time.sleep(sleep_time)
    if "/" not in lib:
        lib = f"library/{lib}"

    AUTH_URL = "https://auth.docker.io"
    REGISTRY_URL = "https://registry.hub.docker.com"
    AUTH_SCOPE = f"repository:{lib}:pull"

    url = f"{AUTH_URL}/token?service=registry.docker.io&scope={AUTH_SCOPE}"

    resp = requests.get(url)
    token = resp.json()["token"]

    if not token:
        log.critical("Invalid docker hub token")
        sys.exit(1)

    headers = {"Authorization": f"Bearer {token}"}

    url = f"{REGISTRY_URL}/v2/{lib}/tags/list"
    resp = requests.get(url, headers=headers)
    tags = resp.json().get("tags")

    if lib == "library/node":
        return get_latest_version(tags, suffix="-buster")

    if lib == "library/rabbitmq":
        return get_latest_version(tags, suffix="-management")

    if lib == "library/ubuntu":
        return get_latest_version(
            tags, regexp=SEMVER2, ignores=["20.10", "21.04", "21.10"]
        )

    if lib == "library/postgres":
        return get_latest_version(tags, regexp=SEMVER2, suffix="-alpine")

    if lib == "library/nginx":
        return get_latest_version(tags, suffix="-alpine")

    return get_latest_version(tags)


def parseDockerfile(
    d: str,
    dependencies: Dependencies,
    skip_angular: bool,
    skip_docker: bool,
    skip_python: bool,
) -> Dependencies:
    with open(d) as f:
        service = d.replace("../build-templates/", "")
        service = service.replace("/Dockerfile", "")
        dependencies.setdefault(service, {})

        for line in f:

            if line.startswith("#"):
                continue

            if not skip_docker and "FROM" in line:
                line = line.replace("FROM", "").strip()
                dependencies[service]["Dockerfile"] = [line]
            elif not skip_angular and (
                "RUN npm install" in line
                or "RUN yarn add" in line
                or "RUN yarn global add" in line
            ):

                tokens = line.split(" ")
                for t in tokens:
                    t = t.strip()
                    if "@" in t:
                        dependencies.setdefault(service, {})
                        dependencies[service].setdefault("npm", [])
                        dependencies[service]["npm"].append(t)
            elif not skip_python and (
                "RUN pip install" in line or "RUN pip3 install" in line
            ):

                tokens = line.split(" ")
                for t in tokens:
                    t = t.strip()
                    if "==" in t:
                        dependencies.setdefault(service, {})
                        dependencies[service].setdefault("pip", [])
                        dependencies[service]["pip"].append(t)

    return dependencies


def parseRequirements(d: str, dependencies: Dependencies) -> Dependencies:
    with open(d) as f:
        service = d.replace("../build-templates/", "")
        service = service.replace("/requirements.txt", "")
        for line in f:
            line = line.strip()

            dependencies.setdefault(service, {})
            dependencies[service].setdefault("pip", [])
            dependencies[service]["pip"].append(line)

    return dependencies


def parsePackageJson(package_json: Path, dependencies: Dependencies) -> Dependencies:
    if not package_json.exists():
        return dependencies

    with open(package_json) as f:
        package = json.load(f)
        package_dependencies = package.get("dependencies", {})
        package_devDependencies = package.get("devDependencies", {})

        dependencies.setdefault("angular", {})
        dependencies["angular"].setdefault("package.json", [])
        dependencies["angular"].setdefault("dev-package.json", [])

        for dep in package_dependencies:
            ver = package_dependencies[dep]
            lib = f"{dep}:{ver}"
            dependencies["angular"]["package.json"].append(lib)
        for dep in package_devDependencies:
            ver = package_devDependencies[dep]
            lib = f"{dep}:{ver}"
            dependencies["angular"]["dev-package.json"].append(lib)

    return dependencies


@click.command()
@click.option("--skip-angular", is_flag=True, default=False)
@click.option("--skip-docker", is_flag=True, default=False)
@click.option("--skip-python", is_flag=True, default=False)
@click.option("--npm-timeout", default=1)
def check_versions(
    skip_angular: bool = False,
    skip_docker: bool = False,
    skip_python: bool = False,
    npm_timeout: int = 1,
    dockerhub_timeout: int = 1,
) -> None:

    dependencies: Dependencies = {}

    if not skip_docker:
        backend = load_yaml_file(Path("controller/confs/backend.yml"))
        services = backend.get("services", {})
        for service in services:
            definition = services.get(service)
            image = definition.get("image")

            image = image.replace("${REGISTRY_HOST}", "")

            if image.startswith("rapydo/"):
                continue
            dependencies.setdefault(service, {})

            dependencies[service]["compose"] = [image]

    for d in glob("../build-templates/*/Dockerfile"):
        if "not_used_anymore_" in d:
            continue

        dependencies = parseDockerfile(
            d, dependencies, skip_angular, skip_docker, skip_python
        )

    if not skip_python:
        for d in glob("../build-templates/*/requirements.txt"):

            dependencies = parseRequirements(d, dependencies)

    if not skip_angular:

        dependencies = parsePackageJson(
            Path("../rapydo-angular/src/package.json"), dependencies
        )

    controller: Any = distutils.core.run_setup("../do/setup.py")
    http_api: Any = distutils.core.run_setup("../http-api/setup.py")

    if not skip_python:
        dependencies["controller"] = {"pip": controller.install_requires}
        dependencies["http-api"] = {"pip": http_api.install_requires}

    filtered_dependencies: Dependencies = {}

    for service, categories in dependencies.items():

        filtered_dependencies.setdefault(service, {})

        for category, deps in categories.items():

            for d in deps:

                filtered_dependencies[service][category] = []

                skipped = False
                if re.match(r"^git\+https://github\.com.*@master$", d):
                    skipped = True
                elif d.endswith(":latest"):
                    skipped = True
                elif "==" in d or ":" in d:
                    filtered_dependencies[service][category].append(d)
                    check_updates(category, d, npm_timeout, dockerhub_timeout)
                elif "@" in d:
                    filtered_dependencies[service][category].append(d)
                    check_updates(category, d, npm_timeout, dockerhub_timeout)
                else:
                    skipped = True

                if skipped:
                    log.debug("Filtering out {}", d)

            if len(filtered_dependencies[service][category]) == 0:
                log.debug("Removing empty list: {}", service)
                del filtered_dependencies[service][category]

        if len(filtered_dependencies[service]) == 0:
            log.debug("Removing empty list: {}", service)
            del filtered_dependencies[service]


if __name__ == "__main__":
    check_versions()
