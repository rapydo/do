# -*- coding: utf-8 -*-

import os
import git
from do import GITHUB_SITE, GIT_EXT, GITHUB_RAPYDO_COMPANY, PROJECT_DIR
from do.utils.logs import get_logger

log = get_logger(__name__)


def clone(repo, path):

    dest = os.path.join(PROJECT_DIR, path)

    # check if directory exist
    if os.path.exists(dest):
        log.debug(f"Path {dest} already exists")
    else:
        gitobj = git.Repo.clone_from(
            url=f"{GITHUB_SITE}/{GITHUB_RAPYDO_COMPANY}/{repo}.{GIT_EXT}",
            to_path=dest
        )
        print(gitobj)
        log.info(f"Cloned repo {repo} as {path}")

    return


def comparing():
    # from git import Repo
    # obj = Repo('backend')
    # obj.blame(rev='HEAD', file='docker-compose.yml')
    # tmp = obj.commit(rev='177e454ea10713975888b638faab2593e2e393b2')
    # tmp.committed_datetime
    pass


def clone_submodules(frontend=False):

    # Builds templates
    clone("build-templates", path="builds_base")
    # Rapydo core as backend
    clone("http-api", path="backend")

    # Frontend only if requested
    if frontend:
        clone("node-ui", path="frontend")

    return
