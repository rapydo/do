# -*- coding: utf-8 -*-
import os
from controller.compose import Compose
from controller import SUBMODULES_DIR, RAPYDO_CONFS
from controller import PROJECT_DIR, CONTAINERS_YAML_DIRNAME
from controller.utilities.configuration import get_yaml_path
from controller import log


def read_conf_files(project, filename):
    """
    Generic method to find and list:
    - submodules/rapydo-confs/conf/ymlfilename     # required
    - projects/CURRENT_PROJECT/conf/ymlfilename    # optional
    """
    files = []

    basedir = os.path.join(
        os.curdir, SUBMODULES_DIR, RAPYDO_CONFS, CONTAINERS_YAML_DIRNAME
    )
    customdir = os.path.join(
        os.curdir, PROJECT_DIR, project, CONTAINERS_YAML_DIRNAME)

    main_yml = get_yaml_path(file=filename, path=basedir)
    files.append(main_yml)

    custom_yml = get_yaml_path(file=filename, path=customdir)
    if isinstance(custom_yml, str):
        log.debug("Found custom {} specs", filename)
        files.append(custom_yml)

    return files


def __call__(args, project, **kwargs):

    command = 'run'
    dc = Compose(files=read_conf_files(project, 'formatter.yml'))
    options = dc.command_defaults(command=command)

    VANILLA_SUBMODULE = 'vanilla'
    if args.get('submodule', VANILLA_SUBMODULE) == VANILLA_SUBMODULE:
        options['SERVICE'] = 'vanilla-formatter'
    else:
        options['SERVICE'] = 'submodules-formatter'

    dc.command(command, options)
