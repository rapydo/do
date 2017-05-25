# -*- coding: utf-8 -*-

import os
from git import Repo
from do import PROJECT_DIR
from do.utils.logs import get_logger

log = get_logger(__name__)


def clone(online_url, path, branch='master', do=False):

    local_path = os.path.join(PROJECT_DIR, path)

    # check if directory exist
    if os.path.exists(local_path):
        gitobj = Repo(local_path)
        # log.debug(f"(CHECKED)\tPath {local_path} already exists")
        log.debug("(CHECKED)\tPath %s already exists" % local_path)
    elif do:
        gitobj = Repo.clone_from(url=online_url, to_path=local_path)
        log.info("Cloned repo %s as %s" % (online_url, path))
    else:
        log.critical_exit("Repo %s missing as %s" % (online_url, local_path))

    # switch

    return comparing(gitobj, branch, online_url=online_url)


def comparing(gitobj, branch, online_url):

    origin = gitobj.remote()
    url = list(origin.urls).pop(0)
    if online_url != url:
        log.critical_exit(
            """
Unmatched local remote: %s\nExpected: %s
Suggestion: remove the directory %s
            """ % (url, online_url, gitobj.working_dir))
    else:
        pass

    if branch != str(gitobj.active_branch):
        log.critical_exit(
            "Wrong branch %s, expected %s.\nSuggested: cd %s; git checkout %s;"
            % (gitobj.active_branch, branch, gitobj.working_dir, branch)
        )
    else:
        pass

    # gitobj.commit()

    # gitobj.blame(rev='HEAD', file='docker-compose.yml')
    # tmp = obj.commit(rev='177e454ea10713975888b638faab2593e2e393b2')
    # tmp.committed_datetime
