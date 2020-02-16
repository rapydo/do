# -*- coding: utf-8 -*-

import os
import sys
from datetime import datetime
from urllib.parse import urlparse

import pytz
from git import Repo
from git.exc import InvalidGitRepositoryError, GitCommandError
from controller import SUBMODULES_DIR, TESTING
from controller import log


def get_repo(path):
    return Repo(path)


def get_local(path):
    try:
        gitobj = get_repo(path)

        if len(gitobj.remotes) == 0:
            log.warning("Unable to fetch remotes from {}", path)
            return None
        return gitobj.remotes.origin.url
    except InvalidGitRepositoryError:
        return None


def get_active_branch(gitobj):

    if gitobj is None:
        log.error("git object is None, cannot retrieve active branch")
        return None
    try:
        return str(gitobj.active_branch)
    except TypeError as e:
        log.warning(e)
        return None


def switch_branch(gitobj, branch_name='master', remote=True):

    if branch_name is None:
        log.error("Unable to switch to a none branch")
        return False

    if gitobj.active_branch.name == branch_name:
        path = os.path.basename(gitobj.working_dir)
        log.info("You are already on branch {} on {}", branch_name, path)
        return False

    if remote:
        branches = gitobj.remotes[0].fetch()
    else:
        branches = gitobj.branches

    branch = None
    branch_found = False
    for branch in branches:
        if remote:
            branch_found = branch.name.endswith('/' + branch_name)
        else:
            branch_found = branch.name == branch_name

        if branch_found:
            break

    if not branch_found or branch is None:
        log.warning("Branch {} not found", branch_name)
        return False

    try:
        gitobj.git.checkout(branch_name)
    except GitCommandError as e:
        log.warning(e)
        return False

    path = os.path.basename(gitobj.working_dir)
    log.info("Switched branch to {} on {}", branch, path)
    return True


def clone(online_url, path, branch='master', do=False, check=True, expand_path=True):

    if expand_path:
        local_path = os.path.join(os.curdir, SUBMODULES_DIR, path)
    else:
        local_path = path
    local_path_exists = os.path.exists(local_path)

    if local_path_exists:
        log.debug("Path {} already exists", local_path)
        gitobj = Repo(local_path)
    elif do:
        gitobj = Repo.clone_from(url=online_url, to_path=local_path)
        log.info("Cloned repo {}@{} as {}", online_url, branch, path)
    else:
        log.exit(
            "Repo {} missing as {}. You should init your project".format(
                online_url, local_path)
        )

    if do:
        switch_branch(gitobj, branch)

    if check:
        compare_repository(gitobj, branch, online_url=online_url, path=path)

    return gitobj


def compare_repository(gitobj, branch, online_url, check_only=False, path=None):

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
            log.exit(
                """Unmatched local remote
Found: {}\nExpected: {}
Suggestion: remove {} and execute the init command
            """.format(url, online_url, gitobj.working_dir)
            )

    if branch is None:
        # No more checks, we are ok
        return True

    active_branch = get_active_branch(gitobj)

    if active_branch is not None:
        if branch != active_branch:
            if check_only:
                return False
            log.exit(
                """{p}: wrong branch {ab}, expected {b}.
Suggestion:\n\ncd {wdir}; git fetch; git checkout {b}; cd -;\n""".format(
                    p=path, ab=active_branch, b=branch, wdir=gitobj.working_dir
                )
            )
    return True


def timestamp_from_string(timestamp_string):
    precision = float(timestamp_string)

    utc_dt = datetime.utcfromtimestamp(precision)
    aware_utc_dt = utc_dt.replace(tzinfo=pytz.utc)

    return aware_utc_dt


def check_file_younger_than(gitobj, filename, timestamp):

    try:
        commits = gitobj.blame(rev='HEAD', file=filename)
    except GitCommandError as e:
        log.exit("Failed 'blame' operation on {}.\n{}", filename, e)
    dates = []
    for commit in commits:
        current_blame = gitobj.commit(rev=str(commit[0]))
        dates.append(current_blame.committed_datetime)

    m = max(dates)
    return timestamp_from_string(timestamp) < m, timestamp, m


def get_unstaged_files(gitobj):
    """
    ref:
    http://gitpython.readthedocs.io/en/stable/tutorial.html#obtaining-diff-information
    """

    diff = []
    diff.extend(gitobj.index.diff(gitobj.head.commit))
    diff.extend(gitobj.index.diff(None))
    return {"changed": diff, "untracked": gitobj.untracked_files}


def print_diff(gitobj, unstaged):

    changed = len(unstaged['changed']) > 0
    untracked = len(unstaged['untracked']) > 0
    if not changed and not untracked:
        return False

    repo_folder = gitobj.working_dir.replace(os.getcwd(), '')
    if repo_folder.startswith('/'):
        repo_folder = repo_folder[1:]
    if not repo_folder.endswith('/'):
        repo_folder += '/'
    if repo_folder == "/":
        repo_folder = ''

    if changed:
        print("\nChanges not staged for commit:")
        for f in unstaged['changed']:
            print("\t{}{}".format(repo_folder, f.a_path))
        print("")
    if untracked:
        print("\nUntracked files:")
        for f in unstaged['untracked']:
            print("\t{}{}".format(repo_folder, f))
        print("")

    return True


def update(path, gitobj):

    unstaged = get_unstaged_files(gitobj)
    changed = len(unstaged['changed']) > 0
    untracked = len(unstaged['untracked']) > 0

    if changed or untracked:
        log.critical("Unable to update {} repo, you have unstaged files", path)
        print_diff(gitobj, unstaged)
        sys.exit(1)

    for remote in gitobj.remotes:
        if remote.name == 'origin':
            try:
                branch = gitobj.active_branch
                log.info("Updating {} {} (branch {})", remote, path, branch)
                remote.pull(branch)
            except GitCommandError as e:
                log.error("Unable to update {} repo\n{}", path, e)
            except TypeError as e:
                if TESTING:
                    log.warning("Unable to update {} repo, {}", path, e)
                else:
                    log.exit("Unable to update {} repo, {}", path, e)


def check_unstaged(path, gitobj):

    unstaged = get_unstaged_files(gitobj)
    if len(unstaged['changed']) > 0 or len(unstaged['untracked']) > 0:
        log.warning("You have unstaged files on {}", path)
    print_diff(gitobj, unstaged)
    return unstaged


def fetch(path, gitobj, fetch_remote='origin'):

    for remote in gitobj.remotes:
        if remote.name != fetch_remote:
            log.verbose("Skipping fetch of remote {} on {}", remote, path)
            continue
        log.verbose("Fetching {} on {}", remote, path)
        try:
            remote.fetch()
        except GitCommandError as e:
            log.exit(str(e))


def check_updates(path, gitobj, fetch_remote='origin', remote_branch=None):

    fetch(path, gitobj, fetch_remote)

    branch = get_active_branch(gitobj)
    if branch is None:
        log.warning("{} repo is detached? Unable to verify updates!", path)
        return False

    if remote_branch is None:
        remote_branch = branch

    max_remote = 20
    log.verbose("Inspecting {}/{}", path, branch)

    # CHECKING COMMITS BEHIND (TO BE PULLED) #
    behind_check = "{}..{}/{}".format(branch, fetch_remote, remote_branch)
    commits_behind = gitobj.iter_commits(behind_check, max_count=max_remote)

    try:
        commits_behind_list = list(commits_behind)
    except GitCommandError:
        log.info(
            "Remote branch {} not found for {} repo. Is it a local branch?".format(
                branch, path)
        )
    else:

        if len(commits_behind_list) > 0:
            log.warning("{} repo should be updated!", path)
        else:
            log.debug("{} repo is updated", path)
        for c in commits_behind_list:
            message = c.message.strip().replace('\n', "")

            sha = c.hexsha[0:7]
            if len(message) > 60:
                message = message[0:57] + "..."
            log.warning("Missing commit from {}: {} ({})", path, sha, message)

    # CHECKING COMMITS AHEAD (TO BE PUSHED) #
    # if path != 'upstream' and remote_branch == branch:
    if remote_branch == branch:
        ahead_check = "{}/{}..{}".format(fetch_remote, remote_branch, branch)
        commits_ahead = gitobj.iter_commits(ahead_check, max_count=max_remote)
        try:
            commits_ahead_list = list(commits_ahead)
        except GitCommandError:
            log.info(
                "Remote branch {} not found for {}. Is it a local branch?".format(
                    branch, path)
            )
        else:

            if len(commits_ahead_list) > 0:
                log.warning("You have commits not pushed on {} repo", path)
            else:
                log.debug("You pushed all commits on {} repo", path)
            for c in commits_ahead_list:
                message = c.message.strip().replace('\n', "")

                sha = c.hexsha[0:7]
                if len(message) > 60:
                    message = message[0:57] + "..."
                log.warning("Unpushed commit in {}: {} ({})", path, sha, message)

    return True
