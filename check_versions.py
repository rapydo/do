# -*- coding: utf-8 -*-

import click
import json
import os
import re
import yaml
import distutils.core
from glob import glob
from prettyprinter import pprint as pp
from loguru import logger as log


def load_yaml_file(filepath):

    log.debug("Reading file {}", filepath)

    if filepath is None or not os.path.exists(filepath):
        log.warning("Failed to read YAML file {}: File does not exist", filepath)
        return {}

    with open(filepath) as fh:
        try:
            loader = yaml.load_all(fh, yaml.loader.Loader)

            docs = list(loader)

            if len(docs) == 0:
                log.exit("YAML file is empty: {}", filepath)

            return docs[0]

        except Exception as e:

            log.warning("Failed to read YAML file [{}]: {}", filepath, e)
            return {}


def check_updates(category, lib):

    if category in ['pip', 'controller', 'http-api']:
        if "==" in lib:
            token = lib.split("==")
        elif ">=" in lib:
            token = lib.split(">=")
        else:
            log.critical("Invalid lib format: {}", lib)

        print('https://pypi.org/project/{}/{}'.format(token[0], token[1]))
    elif category in ['compose', 'Dockerfile']:
        token = lib.split(":")
        print("https://hub.docker.com/_/{}?tab=tags".format(token[0]))
    elif category in ['package.json', 'npm']:
        token = lib.split(":")
        print("https://www.npmjs.com/package/{}".format(token[0]))
    elif category in ['ACME']:
        token = lib.split(":")
        print("https://github.com/Neilpang/acme.sh/releases/tag/{}".format(token[1]))
    else:
        log.critical("{}: {}", category, lib)


@click.command()
@click.option('--skip-angular', is_flag=True, default=False)
def check_versions(skip_angular=False):

    dependencies = {}

    backend = load_yaml_file("../rapydo-confs/confs/backend.yml")
    services = backend.get("services", {})
    for service in services:
        definition = services.get(service)
        image = definition.get('image')

        if image.startswith("rapydo/"):
            continue
        if service not in dependencies:
            dependencies[service] = {}

        dependencies[service]['compose'] = image

    for d in glob("../build-templates/*/Dockerfile"):
        if 'not_used_anymore_' in d:
            continue
        with open(d) as f:
            service = d.replace("../build-templates/", "")
            service = service.replace("/Dockerfile", "")
            if service not in dependencies:
                dependencies[service] = {}

            for line in f:

                if line.startswith("#"):
                    continue

                if 'FROM' in line:
                    line = line.replace("FROM", "").strip()

                    dependencies[service]['Dockerfile'] = line
                elif not skip_angular and 'RUN npm install' in line:
                    if line.startswith("#"):
                        continue

                    tokens = line.split(" ")
                    for t in tokens:
                        t = t.strip()
                        if '@' in t:
                            if service not in dependencies:
                                dependencies[service] = {}
                            if "npm" not in dependencies[service]:
                                dependencies[service]["npm"] = []
                            dependencies[service]["npm"].append(t)
                elif 'RUN pip install' in line or 'RUN pip3 install' in line:
                    if line.startswith("#"):
                        continue
                    tokens = line.split(" ")
                    for t in tokens:
                        t = t.strip()
                        if '==' in t:
                            if service not in dependencies:
                                dependencies[service] = {}
                            if "pip" not in dependencies[service]:
                                dependencies[service]["pip"] = []
                            dependencies[service]["pip"].append(t)
                elif 'ENV ACMEV' in line:
                    line = line.replace("ENV ACMEV", "").strip()
                    line = line.replace("\"", "").strip()

                    dependencies[service]['ACME'] = "ACME:{}".format(line)

    for d in glob("../build-templates/*/requirements.txt"):

        with open(d) as f:
            service = d.replace("../build-templates/", "")
            service = service.replace("/requirements.txt", "")
            for line in f:
                line = line.strip()

                if service not in dependencies:
                    dependencies[service] = {}

                if "pip" not in dependencies[service]:
                    dependencies[service]["pip"] = []

                dependencies[service]["pip"].append(line)

    if not skip_angular:
        package_json = None

        if os.path.exists('../frontend/src/package.json'):
            package_json = '../frontend/src/package.json'
        elif os.path.exists('../rapydo-angular/src/package.json'):
            package_json = '../rapydo-angular/src/package.json'

        if package_json is not None:
            with open(package_json) as f:
                package = json.load(f)
                package_dependencies = package.get('dependencies', {})
                package_devDependencies = package.get('devDependencies', {})

                if 'angular' not in dependencies:
                    dependencies['angular'] = {}

                if "package.json" not in dependencies['angular']:
                    dependencies['angular']["package.json"] = []

                for dep in package_dependencies:
                    ver = package_dependencies[dep]
                    lib = "{}:{}".format(dep, ver)
                    dependencies['angular']["package.json"].append(lib)
                for dep in package_devDependencies:
                    ver = package_devDependencies[dep]
                    lib = "{}:{}".format(dep, ver)
                    dependencies['angular']["package.json"].append(lib)

    controller = distutils.core.run_setup("../do/setup.py")
    http_api = distutils.core.run_setup("../http-api/setup.py")

    dependencies['controller'] = controller.install_requires
    dependencies['http-api'] = http_api.install_requires

    filtered_dependencies = {}

    for service in dependencies:
        if service in ['talib', 'react', 'icat']:
            continue

        service_dependencies = dependencies[service]

        if isinstance(service_dependencies, list):
            filtered_dependencies[service] = []

            for d in service_dependencies:

                skipped = False
                if '==' not in d and '>=' not in d:
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
                if service not in filtered_dependencies:
                    filtered_dependencies[service] = {}
                deps = service_dependencies[category]

                was_str = False
                if isinstance(deps, str):
                    deps = [deps]
                    was_str = True
                else:
                    filtered_dependencies[service][category] = []

                for d in deps:

                    skipped = False
                    if d == 'b2safe/server:icat':
                        skipped = True
                    elif d == 'node:carbon':
                        skipped = True
                    elif re.match(r'^git\+https://github\.com.*@master$', d):
                        skipped = True
                    elif d == 'docker:dind':
                        skipped = True
                    elif d.endswith(':latest'):
                        skipped = True
                    elif '==' in d or ':' in d:

                        if was_str:
                            filtered_dependencies[service][category] = d
                            check_updates(category, d)
                        else:
                            filtered_dependencies[service][category].append(d)
                            check_updates(category, d)
                    elif '@' in d:
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

    log.info("Note: very hard to upgrade ubuntu:16.04 from backendirods and icat")
    log.info("gssapi: versions >1.5.1 does not work and requires some effort...")
    log.info("typescript: angular.cli 8.2.14 requires typescript < 3.6.0, so that max ver is 3.5.3, cannot upgade to ver 3.7.3")


if __name__ == '__main__':
    check_versions()
