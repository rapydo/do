import distutils.core
import json
import os
import re
import sys
import time
from datetime import datetime
from glob import glob
from pathlib import Path
from typing import Any, Dict, List

import click
import requests
import yaml
from bs4 import BeautifulSoup
from glom import glom
from loguru import logger as log
from prettyprinter import pprint as pp

# change current dir to the folder containing this script
# this way the script will be allowed to access all required files
# by providing relative links
os.chdir(os.path.dirname(__file__))

known_update = "2020-11-05"
known_latests = {
    # https://hub.docker.com/_/neo4j?tab=tags
    # https://hub.docker.com/_/postgres?tab=tags
    # https://hub.docker.com/_/mariadb?tab=tags
    # https://hub.docker.com/_/mongo?tab=tags
    # https://hub.docker.com/_/redis?tab=tags
    # https://hub.docker.com/_/nginx?tab=tags
    # https://hub.docker.com/_/node?tab=tags
    # https://hub.docker.com/_/rabbitmq?tab=tags
    # https://hub.docker.com/_/adminer?tab=tags
    # https://hub.docker.com/_/mongo-express?tab=tags
    # https://hub.docker.com/r/fanout/pushpin/tags
    # https://hub.docker.com/r/swaggerapi/swagger-ui/tags
    "docker": {
        "neo4j": "4.1.3",
        "postgres": "13.0-alpine",
        "mariadb": "10.5.6",
        "mongo": "4.4.1",
        "redis": "6.0.9",
        "nginx": "1.19.3-alpine",
        "node": "14.15.0-buster",
        "rabbitmq": "3.8.9-management",
        "adminer": "4.7.7-standalone",
        "mongo-express": "0.54.0",
        "fanout/pushpin": "1.30.0",
        "swaggerapi/swagger-ui": "v3.36.0",
        "stilliard/pure-ftpd": "stretch-latest",
        "ubuntu": "20.04",
    },
    # https://github.com/acmesh-official/acme.sh/releases
    "acme": "2.8.7",
    # Not used
    "urls": {
        "isort": "5.5.2",
        "prettier": "2.1.1",
        "pyupgrade": "v2.7.2",
        "black": "20.8b1",
        "flake8": "3.8.3",
    },
}

prevent_duplicates = {}

now = datetime.now().strftime("%Y-%m-%d")
if now != known_update:
    log.warning("List of known latests is obsolete, ignoring it")
    known_latests = {}


def load_yaml_file(filepath):

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


def check_updates(category, lib, npm_timeout):

    if category == "pip":
        if "==" in lib:
            tokens = lib.split("==")
        elif ">=" in lib:
            return None
            # tokens = lib.split(">=")
        else:
            log.critical("Invalid lib format: {}", lib)
            sys.exit(1)

        if "[" in tokens[0]:
            tokens[0] = tokens[0].split("[")[0]

        # url = f"https://pypi.org/project/{tokens[0]}/{tokens[1]}"
        url = f"https://pypi.org/project/{tokens[0]}"
        latest = parse_pypi(url, tokens[0])

        if latest != tokens[1]:
            print(f"# {tokens[1]} -> {latest}")
            print(url)
            print("")

    elif category in ["compose", "Dockerfile"]:
        tokens = lib.split(":")
        latest = glom(known_latests, f"docker.{tokens[0]}", default="????")

        if latest == "????":
            log.warning("Unknown latest version for {}", tokens[0])

        if latest != tokens[1]:
            print(f"# {tokens[1]} -> {latest}")
            if "/" in tokens[0]:
                print(f"https://hub.docker.com/r/{tokens[0]}?tab=tags")
            else:
                print(f"https://hub.docker.com/_/{tokens[0]}?tab=tags")
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
        time.sleep(npm_timeout)
        latest = parse_npm(url, tokens[0])

        if latest != tokens[1]:
            print(f"# {tokens[1]} -> {latest}")
            print(url)
            print("")

    elif category in ["ACME"]:
        tokens = lib.split(":")

        latest = glom(known_latests, "acme", default="????")

        if latest == "????":
            log.warning("Unknown latest version acme.sh")

        if latest != tokens[1]:
            print(f"# {tokens[1]} -> {latest}")
            print(f"https://github.com/Neilpang/acme.sh/releases/tag/{tokens[1]}")
            print("")
    elif category == "url":
        if lib not in prevent_duplicates:

            prevent_duplicates[lib] = True
            tokens = lib.split("/")
            latest = glom(known_latests, f"urls.{tokens[4]}", default="????")
            if latest != tokens[7]:
                print(f"# {tokens[7]} -> {latest}")
                print(lib)
                print("")
    else:
        log.critical("{}: {}", category, lib)


def parse_npm(url, lib):

    page = requests.get(url)
    soup = BeautifulSoup(page.content, "html5lib")
    span = soup.find("span", attrs={"title": lib})
    if span is None:
        log.error("Span not found for: {} ({})", lib, url)
        return "unknown"

    return span.next_element.next_element.text.split("\xa0")[0]


def parse_pypi(url, lib):

    page = requests.get(url)
    soup = BeautifulSoup(page.content, "html5lib")
    span = soup.find("h1", attrs={"class": "package-header__name"})

    if span is None:
        log.critical("Cannot find pip-command for {}", lib)

    return span.text.strip().replace(f"{lib} ", "").strip()


def parseDockerfile(
    d: str,
    dependencies: Dict[str, Dict[str, List[str]]],
    skip_angular: bool,
) -> Dict[str, Dict[str, List[str]]]:
    with open(d) as f:
        service = d.replace("../build-templates/", "")
        service = service.replace("/Dockerfile", "")
        dependencies.setdefault(service, {})

        for line in f:

            if line.startswith("#"):
                continue

            if "FROM" in line:
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
            elif "RUN pip install" in line or "RUN pip3 install" in line:

                tokens = line.split(" ")
                for t in tokens:
                    t = t.strip()
                    if "==" in t:
                        dependencies.setdefault(service, {})
                        dependencies[service].setdefault("pip", [])
                        dependencies[service]["pip"].append(t)
            elif "ENV ACMEV" in line:
                line = line.replace("ENV ACMEV", "").strip()
                line = line.replace('"', "").strip()

                dependencies[service]["ACME"] = [f"ACME:{line}"]

    return dependencies


def parseRequirements(d, dependencies):
    with open(d) as f:
        service = d.replace("../build-templates/", "")
        service = service.replace("/requirements.txt", "")
        for line in f:
            line = line.strip()

            dependencies.setdefault(service, {})
            dependencies[service].setdefault("pip", [])
            dependencies[service]["pip"].append(line)

    return dependencies


def parsePackageJson(package_json, dependencies):
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


def parsePrecommitConfig(
    f: Path, dependencies: Dict[str, Dict[str, List[str]]], key: str
) -> Dict[str, Dict[str, List[str]]]:

    dependencies.setdefault("precommit", {})
    dependencies["precommit"].setdefault(key, [])
    if not f.exists():
        return dependencies

    y = load_yaml_file(f)
    for r in y.get("repos"):
        rev = r.get("rev")
        repo = r.get("repo")
        if "gitlab" in repo:
            u = f"{repo}/-/tags/{rev}"
        else:
            u = f"{repo}/releases/tag/{rev}"
        dependencies["precommit"][key].append(u)

    return dependencies


@click.command()
@click.option("--skip-angular", is_flag=True, default=False)
@click.option("--npm-timeout", default=1)
@click.option("--verbose", is_flag=True, default=False)
def check_versions(
    skip_angular: bool = False, npm_timeout: int = 1, verbose: bool = False
) -> None:

    dependencies: Dict[str, Dict[str, List[str]]] = {}

    backend = load_yaml_file(Path("controller/confs/backend.yml"))
    services = backend.get("services", {})
    for service in services:
        definition = services.get(service)
        image = definition.get("image")

        if image.startswith("rapydo/"):
            continue
        dependencies.setdefault(service, {})

        dependencies[service]["compose"] = [image]

    for d in glob("../build-templates/*/Dockerfile"):
        if "not_used_anymore_" in d:
            continue

        dependencies = parseDockerfile(d, dependencies, skip_angular)

    for d in glob("../build-templates/*/requirements.txt"):

        dependencies = parseRequirements(d, dependencies)

    if not skip_angular:

        dependencies = parsePackageJson(
            Path("../rapydo-angular/src/package.json"), dependencies
        )

    controller: Any = distutils.core.run_setup("../do/setup.py")
    http_api: Any = distutils.core.run_setup("../http-api/setup.py")

    dependencies["controller"] = {}
    dependencies["controller"]["pip"] = controller.install_requires

    dependencies["http-api"] = {}
    dependencies["http-api"]["pip"] = http_api.install_requires

    dependencies = parsePrecommitConfig(
        Path("../do/.pre-commit-config.yaml"), dependencies, "controller"
    )

    dependencies = parsePrecommitConfig(
        Path("../http-api/.pre-commit-config.yaml"),
        dependencies,
        "http-api",
    )

    dependencies = parsePrecommitConfig(
        Path("../rapydo-angular/.pre-commit-config.yaml"),
        dependencies,
        "rapydo-angular",
    )

    filtered_dependencies: Dict[str, Dict[str, List[str]]] = {}

    for service, categories in dependencies.items():

        filtered_dependencies.setdefault(service, {})

        for category, deps in categories.items():

            for d in deps:

                filtered_dependencies[service][category] = []

                if service == "precommit":

                    skipped = False
                    # repos from pre-commit (github)
                    if "/releases/tag/" in d:
                        filtered_dependencies[service][category].append(d)
                        check_updates("url", d, npm_timeout)
                    # repos from pre-commit (gitlab)
                    elif "/tags/" in d:
                        filtered_dependencies[service][category].append(d)
                        check_updates("url", d, npm_timeout)
                    elif "==" not in d and ">=" not in d:
                        skipped = True
                    else:
                        filtered_dependencies[service][category].append(d)
                        check_updates(service, d, npm_timeout)

                    if skipped:
                        log.debug("Filtering out {}", d)

                else:

                    skipped = False
                    if re.match(r"^git\+https://github\.com.*@master$", d):
                        skipped = True
                    elif d.endswith(":latest"):
                        skipped = True
                    elif "==" in d or ":" in d:
                        filtered_dependencies[service][category].append(d)
                        check_updates(category, d, npm_timeout)
                    elif "@" in d:
                        filtered_dependencies[service][category].append(d)
                        check_updates(category, d, npm_timeout)
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

        # print(service)

    if verbose:
        pp(filtered_dependencies)


if __name__ == "__main__":
    check_versions()

# Changelogs and release notes

# https://raw.githubusercontent.com/antirez/redis/6.0/00-RELEASENOTES
# https://github.com/ngx-formly/ngx-formly/releases
