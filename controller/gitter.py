import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

import pytz
from git import Repo
from git.exc import GitCommandError, InvalidGitRepositoryError, NoSuchPathError

from controller import SUBMODULES_DIR, log


def get_repo(path):
    try:
        return Repo(path)
    except NoSuchPathError:
        return None
    except InvalidGitRepositoryError:  # pragma: no cover
        return None


def init(path):
    return Repo.init(path)


def get_origin(gitobj):
    try:
        if gitobj is None:
            return None

        if len(gitobj.remotes) == 0:
            return None

        url: str = gitobj.remotes.origin.url
        return url
    except AttributeError:
        return None


def get_active_branch(gitobj):

    if gitobj is None:
        log.error("git object is None, cannot retrieve active branch")
        return None
    try:
        return str(gitobj.active_branch)
    except AttributeError as e:
        log.warning(e)
        return None


def switch_branch(gitobj, branch_name="master", remote=True):

    if branch_name is None:
        log.error("Unable to switch to a none branch")
        return False

    current_branch = gitobj.active_branch.name
    if current_branch == branch_name:
        path = Path(gitobj.working_dir).name
        log.info("{} already set on branch {}", path, branch_name)
        return True

    if remote:
        branches = gitobj.remotes[0].fetch()
    else:
        branches = gitobj.branches

    branch = None
    branch_found = False
    for branch in branches:
        if remote:
            branch_found = branch.name.endswith(f"/{branch_name}")
        else:
            branch_found = branch.name == branch_name

        if branch_found:
            break

    if not branch_found or branch is None:
        log.warning("Branch {} not found", branch_name)
        return False

    try:
        gitobj.git.checkout(branch_name)
    except GitCommandError as e:  # pragma: no cover
        log.error(e)
        return False

    path = Path(gitobj.working_dir).name
    log.info("Switched {} branch from {} to {}", path, current_branch, branch_name)
    return True


def clone(url, path, branch, do=False, check=True):

    local_path = SUBMODULES_DIR.joinpath(path)

    if local_path.exists():
        log.debug("Path {} already exists", local_path)
        gitobj = Repo(local_path)
    elif do:
        gitobj = Repo.clone_from(url=url, to_path=local_path)
        log.info("Cloned {}@{} as {}", url, branch, path)
    else:
        log.critical(
            "Repo {} missing as {}. You should init your project",
            url,
            local_path,
        )
        sys.exit(1)

    if do:
        ret = switch_branch(gitobj, branch)
        if not ret:  # pragma: no cover
            log.critical("Cannot switch repo {} to version {}", local_path, branch)
            sys.exit(1)

    if check:
        compare_repository(gitobj, branch, online_url=url, path=path)

    return gitobj


def compare_repository(gitobj, branch, online_url, path=None):

    # origin = gitobj.remote()
    # url = list(origin.urls).pop(0)
    url = gitobj.remotes.origin.url

    if online_url != url:  # pragma: no cover

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
            log.critical(
                """Unmatched local remote
Found: {}\nExpected: {}
Suggestion: remove {} and execute the init command
            """,
                url,
                online_url,
                gitobj.working_dir,
            )
            sys.exit(1)

    active_branch = get_active_branch(gitobj)

    if active_branch is not None:
        if branch != active_branch:
            log.critical(
                "{}: wrong branch {}, expected {}. You can use rapydo init to fix it",
                path,
                active_branch,
                branch,
            )
            sys.exit(1)
    return True


def timestamp_from_string(timestamp_string):
    precision = float(timestamp_string)

    utc_dt = datetime.utcfromtimestamp(precision)
    aware_utc_dt = utc_dt.replace(tzinfo=pytz.utc)

    return aware_utc_dt


def check_file_younger_than(gitobj, filename, timestamp):

    try:
        commits = gitobj.blame(rev="HEAD", file=filename)
    except GitCommandError as e:  # pragma: no cover
        log.critical("Failed 'blame' operation on {}.\n{}", filename, e)
        sys.exit(1)

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

    changed = len(unstaged["changed"]) > 0
    untracked = len(unstaged["untracked"]) > 0
    if not changed and not untracked:
        return False

    repo_folder = str(Path(gitobj.working_dir).relative_to(Path.cwd()))
    if not repo_folder.endswith("/"):
        repo_folder += "/"
    if repo_folder == "/":  # pragma: no cover
        repo_folder = ""

    if changed:
        print("\nChanges not staged for commit:")
        for f in unstaged["changed"]:
            print(f"\t{repo_folder}{f.a_path}")
        print("")
    if untracked:
        print("\nUntracked files:")
        for f in unstaged["untracked"]:
            print(f"\t{repo_folder}{f}")
        print("")

    return True


def update(path, gitobj):

    unstaged = get_unstaged_files(gitobj)
    changed = len(unstaged["changed"]) > 0
    untracked = len(unstaged["untracked"]) > 0

    if changed or untracked:
        log.critical("Unable to update {} repo, you have unstaged files", path)
        print_diff(gitobj, unstaged)
        sys.exit(1)

    for remote in gitobj.remotes:
        if remote.name == "origin":
            try:
                branch = gitobj.active_branch
                log.info("Updating {} {}@{}", remote, path, branch)
                remote.pull(branch)
            except GitCommandError as e:  # pragma: no cover
                log.error("Unable to update {} repo\n{}", path, e)
            except TypeError as e:  # pragma: no cover
                log.critical("Unable to update {} repo, {}", path, e)
                sys.exit(1)


def check_unstaged(path, gitobj):

    unstaged = get_unstaged_files(gitobj)
    if len(unstaged["changed"]) > 0 or len(unstaged["untracked"]) > 0:
        log.warning("You have unstaged files on {}", path)
    print_diff(gitobj, unstaged)
    return unstaged


def fetch(path, gitobj):

    for remote in gitobj.remotes:
        if remote.name == "origin":
            try:
                remote.fetch()
            except GitCommandError as e:  # pragma: no cover
                log.critical(e)
                sys.exit(1)


def check_updates(path, gitobj):

    fetch(path, gitobj)

    branch = get_active_branch(gitobj)
    if branch is None:  # pragma: no cover
        log.warning("Is {} repo detached? Unable to verify updates", path)
        return False

    max_remote = 20

    # CHECKING COMMITS BEHIND (TO BE PULLED) #
    behind_check = f"{branch}..origin/{branch}"
    commits_behind = gitobj.iter_commits(behind_check, max_count=max_remote)

    try:
        commits_behind_list = list(commits_behind)
    except GitCommandError:  # pragma: no cover
        log.info(
            "Remote branch {} not found for {} repo. Is it a local branch?",
            branch,
            path,
        )
    else:

        if not commits_behind_list:
            log.debug("{} repo is updated", path)
        else:  # pragma: no cover
            log.warning("{} repo should be updated!", path)
            for c in commits_behind_list:
                message = c.message.strip().replace("\n", "")

                sha = c.hexsha[0:7]
                if len(message) > 60:
                    message = message[0:57] + "..."
                log.warning("Missing commit from {}: {} ({})", path, sha, message)

    ahead_check = f"origin/{branch}..{branch}"
    commits_ahead = gitobj.iter_commits(ahead_check, max_count=max_remote)
    try:
        commits_ahead_list = list(commits_ahead)
    except GitCommandError:  # pragma: no cover
        log.info(
            "Remote branch {} not found for {}. Is it a local branch?".format(
                branch, path
            )
        )
    else:

        if len(commits_ahead_list) > 0:
            log.warning("You have commits not pushed on {} repo", path)
        else:
            log.debug("You pushed all commits on {} repo", path)
        for c in commits_ahead_list:
            message = c.message.strip().replace("\n", "")

            sha = c.hexsha[0:7]
            if len(message) > 60:  # pragma: no cover
                message = message[0:57] + "..."
            log.warning("Unpushed commit in {}: {} ({})", path, sha, message)

    return True
