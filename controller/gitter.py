# -*- coding: utf-8 -*-

import os
from urllib.parse import urlparse
from git import Repo
from git.exc import InvalidGitRepositoryError, GitCommandError
from controller import SUBMODULES_DIR, TESTING
from utilities import helpers
from utilities.logs import get_logger

log = get_logger(__name__)


def get_repo(path):
    return Repo(path)


def get_local(path):
    try:
        gitobj = get_repo(path)

        if len(gitobj.remotes) == 0:
            log.warning("Unable to fetch remotes from %s" % path)
            return None
        return gitobj.remotes.origin.url
    except InvalidGitRepositoryError:
        return None


def get_active_branch(gitobj):
    try:
        return str(gitobj.active_branch)
    except TypeError as e:
        log.warning(str(e))
        return None


def switch_branch(gitobj, branch_name='master', remote=True):

    if branch_name is None:
        log.error("Unable to switch to a none branch")
        return False

    if gitobj.active_branch.name == branch_name:
        path = os.path.basename(gitobj.working_dir)
        log.info("You are already on branch %s on %s", branch_name, path)
        return False

    if remote:
        branches = gitobj.remotes[0].fetch()
    else:
        branches = gitobj.branches

    branch_found = False
    for branch in branches:
        if remote:
            branch_found = branch.name.endswith('/' + branch_name)
        else:
            branch_found = branch.name == branch_name

        if branch_found:
            break

    if not branch_found:
        log.warning("Branch %s not found", branch_name)
        return False

    try:
        gitobj.git.checkout(branch_name)
    except GitCommandError as e:
        log.warning(str(e))
        return False

    path = os.path.basename(gitobj.working_dir)
    log.info("Switched branch to %s on %s", branch, path)
    return True


def clone(online_url, path, branch='master', do=False):

    local_path = os.path.join(helpers.current_dir(), SUBMODULES_DIR, path)
    local_path_exists = os.path.exists(local_path)

    if local_path_exists:
        log.checked("Path %s already exists" % local_path)
        gitobj = Repo(local_path)
    elif do:
        gitobj = Repo.clone_from(url=online_url, to_path=local_path)
        log.info("Cloned repo %s@%s as %s" % (online_url, branch, path))
    else:
        log.exit("Repo %s missing as %s. You should init your project" % (
            online_url, local_path))

    if do:
        switch_branch(gitobj, branch)

    # switch
    compare_repository(gitobj, branch, online_url=online_url, path=path)
    return gitobj


def compare_repository(gitobj, branch, online_url,
                       check_only=False, path=None):

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
            if check_only:
                return False
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

    if branch is None:
        # No more checks, we are ok
        return True

    active_branch = get_active_branch(gitobj)

    if active_branch is not None:
        if branch != active_branch:
            if check_only:
                return False
            log.critical_exit(
                """%s: wrong branch %s, expected %s.
Suggestion:\n\ncd %s; git fetch; git checkout %s; cd -;\n"""
                % (path, active_branch, branch, gitobj.working_dir, branch)
            )
    return True


def check_file_younger_than(gitobj, filename, timestamp):

    try:
        commits = gitobj.blame(rev='HEAD', file=filename)
    except GitCommandError as e:
        log.exit("Failed 'blame' operation on %s.\n%s" % (filename, e))
    dates = []
    for commit in commits:
        current_blame = gitobj.commit(rev=str(commit[0]))
        dates.append(current_blame.committed_datetime)

    # tmp = obj.commit(rev='177e454ea10713975888b638faab2593e2e393b2')

    from utilities import time
    m = max(dates)
    return time.timestamp_from_string(timestamp) < m, timestamp, m


def get_unstaged_files(gitobj):
    """
    ref: http://gitpython.readthedocs.io/en/stable/
        tutorial.html#obtaining-diff-information
    """

    diff = []
    diff.extend(gitobj.index.diff(gitobj.head.commit))
    diff.extend(gitobj.index.diff(None))
    diff.extend(gitobj.untracked_files)
    return diff


def update(path, gitobj):

    has_unstaged = len(get_unstaged_files(gitobj)) > 0

    if has_unstaged:
        log.warning(
            "Unable to update %s repo, you have unstaged files" % (path))
        return

    for remote in gitobj.remotes:
        if remote.name == 'origin':
            try:
                branch = gitobj.active_branch
                log.info("Updating %s %s (branch %s)" % (remote, path, branch))
                remote.pull(branch)
            except GitCommandError as e:
                log.error("Unable to update %s repo\n%s", path, e)
            except TypeError as e:
                if TESTING:
                    log.warning("Unable to update %s repo, %s" % (path, e))
                else:
                    log.exit("Unable to update %s repo, %s" % (path, e))


def check_unstaged(path, gitobj, logme=True):

    unstaged = len(get_unstaged_files(gitobj)) > 0
    if unstaged and logme:
        log.warning("You have unstaged files on %s" % path)
    return unstaged


def fetch(path, gitobj, fetch_remote='origin'):

    for remote in gitobj.remotes:
        if remote.name != fetch_remote:
            log.verbose("Skipping fetch of remote %s on %s" % (remote, path))
            continue
        log.verbose("Fetching %s on %s" % (remote, path))
        try:
            remote.fetch()
        except GitCommandError as e:
            log.exit(str(e))


def check_updates(path, gitobj, fetch_remote='origin', remote_branch=None):

    fetch(path, gitobj, fetch_remote)

    branch = get_active_branch(gitobj)
    if branch is None:
        log.warning("%s repo is detached? Unable to verify updates!" % (path))
        return False

    if remote_branch is None:
        remote_branch = branch

    max_remote = 20
    log.verbose("Inspecting %s/%s" % (path, branch))

    # CHECKING COMMITS BEHIND (TO BE PULLED) #
    behind_check = "%s..%s/%s" % (branch, fetch_remote, remote_branch)
    commits_behind = gitobj.iter_commits(
        behind_check, max_count=max_remote)

    try:
        commits_behind_list = list(commits_behind)
    except GitCommandError:
        log.info(
            "Remote branch %s not found for %s repo. Is it a local branch?"
            % (branch, path)
        )
    else:

        if len(commits_behind_list) > 0:
            log.warning("%s repo should be updated!" % (path))
        else:
            log.checked("%s repo is updated" % (path))
        for c in commits_behind_list:
            message = c.message.strip().replace('\n', "")

            sha = c.hexsha[0:7]
            if len(message) > 60:
                message = message[0:57] + "..."
            log.warning(
                "Missing commit from %s: %s (%s)"
                % (path, sha, message))

    # CHECKING COMMITS AHEAD (TO BE PUSHED) #
    # if path != 'upstream' and remote_branch == branch:
    if remote_branch == branch:
        ahead_check = "%s/%s..%s" % (fetch_remote, remote_branch, branch)
        commits_ahead = gitobj.iter_commits(
            ahead_check, max_count=max_remote)
        try:
            commits_ahead_list = list(commits_ahead)
        except GitCommandError:
            log.info(
                "Remote branch %s not found for %s. Is it a local branch?"
                % (branch, path)
            )
        else:

            if len(commits_ahead_list) > 0:
                log.warning(
                    "You have commits not pushed on %s repo" % (path))
            else:
                log.checked("You pushed all commits on %s repo" % (path))
            for c in commits_ahead_list:
                message = c.message.strip().replace('\n', "")

                sha = c.hexsha[0:7]
                if len(message) > 60:
                    message = message[0:57] + "..."
                log.warning(
                    "Unpushed commit in %s: %s (%s)"
                    % (path, sha, message))

    return True
