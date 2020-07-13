import distutils.core
import json
import os
import re
from glob import glob
from pathlib import Path

import click
import yaml
from loguru import logger as log
from prettyprinter import pprint as pp

# change current dir to the folder containing this script
# this way the script will be allowed to access all required files
# by providing relative links
os.chdir(os.path.dirname(__file__))


def load_yaml_file(filepath):

    log.debug("Reading file {}", filepath)

    if filepath is None or not filepath.exists():
        log.warning("Failed to read YAML file {}: File does not exist", filepath)
        return {}

    with open(filepath) as fh:
        try:
            loader = yaml.load_all(fh, yaml.loader.Loader)

            docs = list(loader)

            if len(docs) == 0:
                log.exit("YAML file is empty: {}", filepath)

            return docs[0]

        except BaseException as e:

            log.warning("Failed to read YAML file [{}]: {}", filepath, e)
            return {}


def check_updates(category, lib):

    if category in ["pip", "controller", "http-api"]:
        if "==" in lib:
            token = lib.split("==")
        elif ">=" in lib:
            token = lib.split(">=")
        else:
            log.critical("Invalid lib format: {}", lib)

        print(f"https://pypi.org/project/{token[0]}/{token[1]}")
    elif category in ["compose", "Dockerfile"]:
        token = lib.split(":")
        print(f"https://hub.docker.com/_/{token[0]}?tab=tags")
    elif category in ["package.json", "npm"]:
        token = lib.split(":")
        print(f"https://www.npmjs.com/package/{token[0]}")
    elif category in ["ACME"]:
        token = lib.split(":")
        print(f"https://github.com/Neilpang/acme.sh/releases/tag/{token[1]}")
    elif category == "url":
        print(lib)
    else:
        log.critical("{}: {}", category, lib)


def parseDockerfile(d, dependencies, skip_angular):
    with open(d) as f:
        service = d.replace("../build-templates/", "")
        service = service.replace("/Dockerfile", "")
        dependencies.setdefault(service, {})

        for line in f:

            if line.startswith("#"):
                continue

            if "FROM" in line:
                line = line.replace("FROM", "").strip()

                dependencies[service]["Dockerfile"] = line
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

                dependencies[service]["ACME"] = f"ACME:{line}"

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

        for dep in package_dependencies:
            ver = package_dependencies[dep]
            lib = f"{dep}:{ver}"
            dependencies["angular"]["package.json"].append(lib)
        for dep in package_devDependencies:
            ver = package_devDependencies[dep]
            lib = f"{dep}:{ver}"
            dependencies["angular"]["package.json"].append(lib)

    return dependencies


def parsePrecommitConfig(f, dependencies, key):

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
        dependencies[key].append(u)

    return dependencies


@click.command()
@click.option("--skip-angular", is_flag=True, default=False)
def check_versions(skip_angular=False):

    dependencies = {}

    backend = load_yaml_file(Path("controller/confs/backend.yml"))
    services = backend.get("services", {})
    for service in services:
        definition = services.get(service)
        image = definition.get("image")

        if image.startswith("rapydo/"):
            continue
        dependencies.setdefault(service, {})

        dependencies[service]["compose"] = image

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

    controller = distutils.core.run_setup("../do/setup.py")
    http_api = distutils.core.run_setup("../http-api/setup.py")

    dependencies["controller"] = controller.install_requires
    dependencies["http-api"] = http_api.install_requires

    dependencies = parsePrecommitConfig(
        Path("../do/.pre-commit-config.yaml"), dependencies, "controller"
    )

    dependencies = parsePrecommitConfig(
        Path("../http-api/.pre-commit-config.yaml"), dependencies, "http-api"
    )

    filtered_dependencies = {}

    for service in dependencies:
        if service in ["talib", "react", "icat"]:
            continue

        service_dependencies = dependencies[service]

        if isinstance(service_dependencies, list):
            filtered_dependencies[service] = []

            for d in service_dependencies:

                skipped = False
                # repos from pre-commit (github)
                if "/releases/tag/" in d:
                    filtered_dependencies[service].append(d)
                    check_updates("url", d)
                # repos from pre-commit (gitlab)
                elif "/tags/" in d:
                    filtered_dependencies[service].append(d)
                    check_updates("url", d)
                elif "==" not in d and ">=" not in d:
                    skipped = True
                else:
                    filtered_dependencies[service].append(d)
                    check_updates(service, d)

                if skipped:
                    log.debug("Filtering out {}", d)

            if len(filtered_dependencies[service]) == 0:
                log.debug("Removing empty list: {}", service)
                del filtered_dependencies[service]

        elif isinstance(service_dependencies, dict):
            for category in service_dependencies:
                filtered_dependencies.setdefault(service, {})
                deps = service_dependencies[category]

                was_str = False
                if isinstance(deps, str):
                    deps = [deps]
                    was_str = True
                else:
                    filtered_dependencies[service][category] = []

                for d in deps:

                    skipped = False
                    if d == "b2safe/server:icat":
                        skipped = True
                    elif d == "node:carbon":
                        skipped = True
                    elif re.match(r"^git\+https://github\.com.*@master$", d):
                        skipped = True
                    elif d == "docker:dind":
                        skipped = True
                    elif d.endswith(":latest"):
                        skipped = True
                    elif "==" in d or ":" in d:

                        if was_str:
                            filtered_dependencies[service][category] = d
                            check_updates(category, d)
                        else:
                            filtered_dependencies[service][category].append(d)
                            check_updates(category, d)
                    elif "@" in d:
                        filtered_dependencies[service][category].append(d)
                        check_updates(category, d)
                    else:
                        skipped = True

                    if skipped:
                        log.debug("Filtering out {}", d)
                if category in filtered_dependencies[service]:
                    if len(filtered_dependencies[service][category]) == 0:
                        log.debug("Removing empty list: {}.{}", service, category)
                        del filtered_dependencies[service][category]
                if len(filtered_dependencies[service]) == 0:
                    log.debug("Removing empty list: {}", service)
                    del filtered_dependencies[service]
        else:
            log.warning("Unknown dependencies type: {}", type(service_dependencies))

        # print(service)

    pp(filtered_dependencies)

    log.info("Very hard to upgrade ubuntu:16.04 from backendirods and icat")
    log.info(
        "oauthlib/requests-oauthlib are blocked by Flask-OAuthlib. Migration to authlib is required"
    )
    log.info("gssapi: versions >1.5.1 does not work and requires some effort...")


if __name__ == "__main__":
    check_versions()

# Changelogs and release notes

# https://raw.githubusercontent.com/antirez/redis/6.0/00-RELEASENOTES
