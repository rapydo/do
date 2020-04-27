# -*- coding: utf-8 -*-
import os
from glom import glom

from controller import PROJECT_DIR
from controller import log

ANGULARJS = 'angularjs'
ANGULAR = 'angular'
REACT = 'react'


def walk_services(actives, dependecies, index=0):

    if index >= len(actives):
        return actives

    next_active = actives[index]

    for service in dependecies.get(next_active, []):
        if service not in actives:
            actives.append(service)

    index += 1
    if index >= len(actives):
        return actives
    return walk_services(actives, dependecies, index)


def find_active(services):
    """
    Check only services involved in current mode,
    which is equal to services 'activated' + 'depends_on'.
    """

    dependencies = {}
    all_services = {}
    base_actives = []

    for service in services:

        name = service.get('name')
        all_services[name] = service
        dependencies[name] = list(service.get('depends_on', {}).keys())

        ACTIVATE = glom(service, "environment.ACTIVATE", default=0)
        is_active = str(ACTIVATE) == "1"
        if is_active:
            base_actives.append(name)

    log.verbose("Base active services = {}", base_actives)
    log.verbose("Services dependencies = {}", dependencies)
    active_services = walk_services(base_actives, dependencies)
    return all_services, active_services


def apply_variables(dictionary, variables):

    new_dict = {}
    for key, value in dictionary.items():
        if isinstance(value, str) and value.startswith('$$'):
            value = variables.get(value.lstrip('$'), None)
        else:
            pass
        new_dict[key] = value

    return new_dict


# move here all checks on project (required files, creation functions, templating, etc)
class Project:

    def __init__(self):
        self.expected_main_folders = [
            PROJECT_DIR,
            'data',
            'submodules'
        ]
        self.expected_folders = []
        self.expected_files = []
        self.data_folders = []
        self.data_files = []
        self.obsolete_files = []

    def p_path(self, *args):
        return os.path.join(PROJECT_DIR, self.project, *args)

    def load_project_scaffold(self, project):
        self.project = project
        self.expected_folders.extend(self.expected_main_folders)
        if self.project is None:
            log.debug("No projected specified")
            return False

        self.expected_folders.append(self.p_path("confs"))
        self.expected_folders.append(self.p_path("backend"))
        self.expected_folders.append(self.p_path("backend", "apis"))
        self.expected_folders.append(self.p_path("backend", "models"))
        self.expected_folders.append(self.p_path("backend", "tests"))

        self.expected_files.append(self.p_path("project_configuration.yaml"))
        self.expected_files.append(self.p_path("confs", "commons.yml"))
        self.expected_files.append(self.p_path("confs", "development.yml"))
        self.expected_files.append(self.p_path("confs", "production.yml"))

        self.data_folders.extend([
            os.path.join("data", "logs")
        ])

        # Deprecated on 0.7.0
        self.obsolete_files.append(self.p_path("backend", "swagger", "models.yaml"))
        self.obsolete_files.append(self.p_path("frontend", "custom.ts"))
        # Deprecated on 0.7.1
        self.obsolete_files.append(self.p_path("confs", "debug.yml"))

        return True

    def load_frontend_scaffold(self, frontend):
        self.frontend = frontend

        if self.frontend is None:
            log.debug("No frontend specified")
            return False

        if self.frontend is not None:
            self.expected_folders.append(self.p_path("frontend"))

        if self.frontend == ANGULAR:
            self.expected_folders.extend([
                self.p_path("frontend", "app"),
                self.p_path("frontend", "css")
            ])

            self.expected_files.extend([
                self.p_path("frontend", "package.json"),
                self.p_path("frontend", "app", "custom.project.options.ts"),
                self.p_path("frontend", "app", "custom.module.ts"),
                self.p_path("frontend", "app", "custom.navbar.ts"),
                self.p_path("frontend", "app", "custom.profile.ts"),
                self.p_path("frontend", "css", "style.css"),
                self.p_path("frontend", "app", "custom.navbar.links.html"),
                self.p_path("frontend", "app", "custom.navbar.brand.html"),
                self.p_path("frontend", "app", "custom.profile.html"),
            ])

            data_dir = os.path.join("data", self.project, "frontend")
            self.data_folders.extend([
                data_dir,
                os.path.join(data_dir, "app"),
                os.path.join(data_dir, "courtesy"),
                os.path.join(data_dir, "e2e"),
                os.path.join(data_dir, "node_modules"),
            ])

            self.data_files.extend([
                os.path.join(data_dir, "angular.json"),
                os.path.join(data_dir, "browserslist"),
                os.path.join(data_dir, "karma.conf.js"),
                os.path.join(data_dir, "package.json"),
                os.path.join(data_dir, "polyfills.ts"),
                os.path.join(data_dir, "tsconfig.app.json"),
                os.path.join(data_dir, "tsconfig.json"),
                os.path.join(data_dir, "tsconfig.spec.json"),
                os.path.join(data_dir, "tslint.json"),
            ])

            self.obsolete_files.extend([
                self.p_path("frontend", "app", "app.routes.ts"),
                self.p_path("frontend", "app", "app.declarations.ts"),
                self.p_path("frontend", "app", "app.providers.ts"),
                self.p_path("frontend", "app", "app.imports.ts"),
                self.p_path("frontend", "app", "app.custom.navbar.ts"),
                self.p_path("frontend", "app", "app.entryComponents.ts"),
                self.p_path("frontend", "app", "app.home.ts"),
                self.p_path("frontend", "app", "app.home.html"),
                self.p_path("frontend", "app", "custom.declarations.ts"),
                self.p_path("frontend", "app", "custom.routes.ts"),
            ])

        if self.frontend == ANGULARJS:

            self.expected_folders.extend([
                self.p_path("frontend", "js"),
                self.p_path("frontend", "templates"),
            ])

            self.expected_files.extend([
                self.p_path("frontend", "js", "app.js"),
                self.p_path("frontend", "js", "routing.extra.js"),
            ])

        return True
