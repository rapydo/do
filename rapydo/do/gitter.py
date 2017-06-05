# -*- coding: utf-8 -*-

import os
from urllib.parse import urlparse
from git import Repo
from git.exc import InvalidGitRepositoryError
from rapydo.utils import helpers
from rapydo.utils.logs import get_logger

log = get_logger(__name__)


def get_local(path):
    try:
        gitobj = Repo(path)
        return gitobj.remotes.origin.url
    except InvalidGitRepositoryError:
        return None


def upstream(url, path=None, key='upstream', do=False):

    if path is None:
        path = helpers.current_dir()

    gitobj = Repo(path)
    try:
        upstream = gitobj.remote(key)
    except ValueError:
        if do:
            upstream = gitobj.create_remote(key, url)
            log.info("Added remote %s: %s" % (key, url))
        else:
            log.critical_exit(
                """Missing upstream to rapydo/core
Suggestion: execute the init command
                """
            )

    current_url = next(upstream.urls)
    if current_url != url:
        if do:
            upstream.set_url(new_url=url, old_url=current_url)
            log.info("Replaced %s to %s" % (key, url))
        else:
            log.critical_exit(
                """Rapydo upstream misconfiguration
Found: %s
Expected: %s
Suggestion: execute the init command
                """
                % (current_url, url)
            )
    else:
        log.debug("(CHECKED) upstream is set correctly")

    return gitobj


def switch_branch(gitobj, branch_name='master'):

    if gitobj.active_branch.name == branch_name:
        return False

    switch = False
    remote_branches = gitobj.remotes[0].fetch()

    for remote_branch in remote_branches:

        if remote_branch.name.endswith('/' + branch_name):
            # Create a new HEAD
            chkout = gitobj.create_head(
                branch_name, remote_branch.commit)
            # Switch to the new HEAD (like checkout)
            gitobj.head.reference = chkout
            # reset the index and working tree to match the pointed-to commit
            gitobj.head.reset(index=True, working_tree=True)
            # Verify that no problem are available
            assert not gitobj.head.is_detached
            log.verbose("Switching %s to %s" % (gitobj.git_dir, branch_name))
            # Signal
            switch = True
            break
        else:
            pass

    if not switch:
        log.critical_exit("Requested branch '%s' was not found" % branch_name)

    return True


def clone(online_url, path, branch='master', do=False):

    local_path = os.path.join(helpers.current_dir(), path)
    local_path_exists = os.path.exists(local_path)
    if local_path_exists:
        log.debug("(CHECKED) path %s already exists" % local_path)
        gitobj = Repo(local_path)
    elif do:
        gitobj = Repo.clone_from(url=online_url, to_path=local_path)
        switch_branch(gitobj, branch)
        log.info("Cloned repo %s@%s as %s" % (online_url, branch, path))
    else:
        log.critical_exit("Repo %s missing as %s" % (online_url, local_path))

    # switch
    comparing(gitobj, branch, online_url=online_url)
    return gitobj


def comparing(gitobj, branch, online_url):

    # origin = gitobj.remote()
    # url = list(origin.urls).pop(0)
    url = gitobj.remotes.origin.url

    if online_url != url:

        local_url = urlparse(url)
        expected_url = urlparse(online_url)

        # Remove username in the URL, if any
        # i.e. youruser@github.com became github.com
        local_netloc = local_url.netloc.split("@").pop()
        expected_netloc = local_url.netloc.split("@").pop()

        if local_url.scheme != expected_url.scheme:
            url_match = False
        elif local_netloc != expected_netloc:
            url_match = False
        elif local_url.path != expected_url.path:
            url_match = False
        else:
            url_match = True

        if not url_match:
            log.critical_exit(
                """Unmatched local remote
Found: %s\nExpected: %s
Suggestion: remove %s and execute the init command
            """ % (url, online_url, gitobj.working_dir))
        # TO FIX: before suggesting to delete verify if the repo is clean
        # i.e. verify if git status find out something is modified
        else:
            log.verbose(
                "Local remote differs but is accepted, found %s, expected: %s)"
                % (url, online_url)
            )

    if branch != str(gitobj.active_branch):
        log.critical_exit(
            "Wrong branch %s, expected %s.\nSuggested: cd %s; git checkout %s;"
            % (gitobj.active_branch, branch, gitobj.working_dir, branch)
        )


def check_file_younger_than(gitobj, file, timestamp):
    # gitobj.commit()
    commits = gitobj.blame(rev='HEAD', file=file)
    dates = []
    for commit in commits:
        current_blame = gitobj.commit(rev=str(commit[0]))
        dates.append(current_blame.committed_datetime)

    # tmp = obj.commit(rev='177e454ea10713975888b638faab2593e2e393b2')

    from rapydo.utils import time
    return time.timestamp_from_string(timestamp) < max(dates)


def check_updates(path, gitobj):

    # TO FIX: to be discussed
    if path == 'main':
        # For now we skip the main repo, because it could be password protected
        return

    for remote in gitobj.remotes:
        log.verbose("Fetching %s" % remote)
        remote.fetch()

    branch = gitobj.active_branch
    remote_branch = "origin/%s" % branch
    max_remote = 20
    log.verbose("Inspecting %s/%s" % (path, branch))
    last_local_commit = list(gitobj.iter_commits(branch, max_count=1)).pop()

    remote_commits = list(
        gitobj.iter_commits(remote_branch, max_count=max_remote))

    log.verbose("Last local commit for %s is %s" % (path, last_local_commit))
    behind = 0
    for c in remote_commits:
        if c == last_local_commit:
            break
        behind += 1
        if behind == 1:
            log.warning("%s repo should be updated!" % (path))

        message = c.message.strip()

        sha = c.hexsha[0:7]
        if len(message) > 60:
            message = message[0:57] + "..."
        log.info(

            "Missing commit in %s: %s (%s)"
            % (path, sha, message))

    if behind == 0:
        log.debug("(CHECKED) %s repo is updated" % (path))
