from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union
from urllib.parse import urlparse

import pytz
from git import Repo
from git.diff import Diff
from git.exc import GitCommandError, InvalidGitRepositoryError, NoSuchPathError

from controller import RED, SUBMODULES_DIR, log, print_and_exit

MAX_FETCHED_COMMITS = 20


def get_repo(path: str) -> Optional[Repo]:
    try:
        return Repo(path)
    except NoSuchPathError:
        return None
    except InvalidGitRepositoryError:  # pragma: no cover
        return None


def init(path: str) -> Repo:
    return Repo.init(path)


def get_origin(gitobj: Optional[Repo]) -> Optional[str]:
    try:
        if not gitobj:
            return None

        if len(gitobj.remotes) == 0:
            return None

        url: str = gitobj.remotes.origin.url
        return url
    except AttributeError:  # pragma: no cover
        return None


def get_active_branch(gitobj: Optional[Repo]) -> Optional[str]:

    if not gitobj:
        log.error("git object is None, cannot retrieve active branch")
        return None
    try:
        return gitobj.active_branch.name
    except AttributeError as e:  # pragma: no cover
        log.warning(e)
        return None


def switch_branch(gitobj: Optional[Repo], branch_name: str) -> bool:

    if not gitobj:
        log.error("git object is None, cannot switch the active branch")
        return False

    current_branch = gitobj.active_branch.name

    path: str = "N/A"
    if gitobj.working_dir:
        path = Path(gitobj.working_dir).name

    if current_branch == branch_name:
        log.info("{} already set on branch {}", path, branch_name)
        return True

    branches = gitobj.remotes[0].fetch()

    branch = None
    for b in branches:
        if b.name.endswith(f"/{branch_name}"):
            branch = b
            break

    if not branch:
        log.warning("Branch {} not found", branch_name)
        return False

    try:
        gitobj.git.checkout(branch_name)
    except GitCommandError as e:  # pragma: no cover
        log.error(e)
        return False

    log.info("Switched {} branch from {} to {}", path, current_branch, branch_name)
    return True


def clone(
    url: str, path: Path, branch: str, do: bool = False, check: bool = True
) -> Repo:

    local_path = SUBMODULES_DIR.joinpath(path)

    if local_path.exists():
        log.debug("Path {} already exists", local_path)
        gitobj = Repo(local_path)
    elif do:
        gitobj = Repo.clone_from(url=url, to_path=local_path)
        log.info("Cloned {}@{} as {}", url, branch, path)
    else:
        print_and_exit(
            "Repo {} missing as {}. You should init your project",
            url,
            local_path,
        )

    if do:
        ret = switch_branch(gitobj, branch)
        if not ret:  # pragma: no cover
            print_and_exit("Cannot switch repo {} to version {}", local_path, branch)

    if check:
        compare_repository(gitobj, branch, online_url=url)

    return gitobj


def compare_repository(gitobj: Repo, branch: str, online_url: str) -> bool:

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
            print_and_exit(
                """Unmatched local remote
Found: {}\nExpected: {}
Suggestion: remove {} and execute the init command
            """,
                url,
                online_url,
                str(gitobj.working_dir or "N/A"),
            )

    active_branch = get_active_branch(gitobj)

    if active_branch and active_branch != branch and gitobj.working_dir:
        print_and_exit(
            "{}: wrong branch {}, expected {}. You can fix it with {command}",
            Path(gitobj.working_dir).stem,
            active_branch,
            branch,
            command=RED("rapydo init"),
        )
    return True


def timestamp_from_string(timestamp_string: Union[str, float]) -> datetime:
    utc_dt = datetime.utcfromtimestamp(float(timestamp_string))
    aware_utc_dt = utc_dt.replace(tzinfo=pytz.utc)

    return aware_utc_dt


def check_file_younger_than(
    gitobj: Repo, filename: Path, timestamp: Union[str, float]
) -> Tuple[bool, float, datetime]:

    try:
        commits = gitobj.blame(rev="HEAD", file=str(filename))
    except GitCommandError:
        log.debug("Can't retrieve a commit history for {}", filename)
        return False, 0, datetime.fromtimestamp(0)

    # added a default date to prevent errors in case of new files with no blame commits
    dates = [datetime.fromtimestamp(0).replace(tzinfo=pytz.utc)]
    if commits:
        for commit in commits:
            current_blame = gitobj.commit(rev=str(commit[0]))
            dates.append(current_blame.committed_datetime)

    max_date = max(dates)
    return (
        bool(timestamp_from_string(timestamp) < max_date),
        float(timestamp),
        max_date,
    )


def get_unstaged_files(gitobj: Repo) -> Dict[str, List[str]]:
    """
    ref:
    http://gitpython.readthedocs.io/en/stable/tutorial.html#obtaining-diff-information
    """

    diff: List[Diff] = []
    diff.extend(gitobj.index.diff(gitobj.head.commit))
    diff.extend(gitobj.index.diff(None))

    return {
        "changed": [d.a_path for d in diff if d.a_path],
        "untracked": gitobj.untracked_files,
    }


def print_diff(gitobj: Repo, unstaged: Dict[str, List[str]]) -> bool:

    changed = len(unstaged["changed"]) > 0
    untracked = len(unstaged["untracked"]) > 0
    if not changed and not untracked:
        return False

    if not gitobj.working_dir:  # pragma: no cover
        return False

    repo_folder = str(Path(gitobj.working_dir).relative_to(Path.cwd()))
    if not repo_folder.endswith("/"):
        repo_folder += "/"
    if repo_folder == "/":  # pragma: no cover
        repo_folder = ""

    if changed:
        print("\nChanges not staged for commit:")
        for f in unstaged["changed"]:
            print(f"\t{repo_folder}{f}")
        print("")
    if untracked:
        print("\nUntracked files:")
        for f in unstaged["untracked"]:
            print(f"\t{repo_folder}{f}")
        print("")

    return True


def can_be_updated(path: str, gitobj: Repo, do_print: bool = True) -> bool:
    unstaged = get_unstaged_files(gitobj)
    updatable = len(unstaged["changed"]) == 0 and len(unstaged["untracked"]) == 0

    if not updatable and do_print:
        log.critical("Unable to update {} repo, you have unstaged files", path)
        print_diff(gitobj, unstaged)

    return updatable


def update(path: str, gitobj: Repo) -> None:

    if not gitobj.active_branch:  # pragma: no cover
        log.error("Can't update {}, no active branch found", path)
        return None

    for remote in gitobj.remotes:
        if remote.name == "origin":
            try:
                branch = gitobj.active_branch.name
                log.info("Updating {} {}@{}", remote, path, branch)

                fetch(path, gitobj)
                commits_behind = gitobj.iter_commits(
                    f"{branch}..origin/{branch}", max_count=MAX_FETCHED_COMMITS
                )
                try:
                    commits_behind_list = list(commits_behind)
                except GitCommandError:  # pragma: no cover
                    log.info(
                        "Remote branch {} not found for {}. Is it a local branch?",
                        branch,
                        path,
                    )
                else:
                    if commits_behind_list:  # pragma: no cover
                        for c in commits_behind_list:
                            message = str(c.message).strip().replace("\n", "")

                            if message.startswith("#"):
                                continue

                            sha = c.hexsha[0:7]
                            if len(message) > 60:
                                message = message[0:57] + "..."
                            log.info("... pulling commit {}: {}", sha, message)

                remote.pull(branch)
            except GitCommandError as e:  # pragma: no cover
                log.error("Unable to update {} repo\n{}", path, e)
            except TypeError as e:  # pragma: no cover
                print_and_exit("Unable to update {} repo, {}", path, str(e))


def check_unstaged(path: str, gitobj: Repo) -> None:

    unstaged = get_unstaged_files(gitobj)
    if len(unstaged["changed"]) > 0 or len(unstaged["untracked"]) > 0:
        log.warning("You have unstaged files on {}", path)
    print_diff(gitobj, unstaged)


def fetch(path: str, gitobj: Repo) -> None:

    for remote in gitobj.remotes:
        if remote.name == "origin":
            try:
                remote.fetch()
            except GitCommandError as e:  # pragma: no cover
                print_and_exit(str(e))


def check_updates(path: str, gitobj: Repo) -> None:

    fetch(path, gitobj)

    branch = get_active_branch(gitobj)
    if branch is None:  # pragma: no cover
        log.warning("Is {} repo detached? Unable to verify updates", path)
        return None

    # CHECKING COMMITS BEHIND (TO BE PULLED) #
    commits_behind = gitobj.iter_commits(
        f"{branch}..origin/{branch}", max_count=MAX_FETCHED_COMMITS
    )

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
                message = str(c.message).strip().replace("\n", "")

                if message.startswith("#"):
                    continue

                sha = c.hexsha[0:7]
                if len(message) > 60:
                    message = message[0:57] + "..."
                log.warning("... missing commit from {}: {} ({})", path, sha, message)

    commits_ahead = gitobj.iter_commits(
        f"origin/{branch}..{branch}", max_count=MAX_FETCHED_COMMITS
    )
    try:
        commits_ahead_list = list(commits_ahead)
    except GitCommandError:  # pragma: no cover
        log.info(
            "Remote branch {} not found for {}. Is it a local branch?", branch, path
        )
    else:

        if len(commits_ahead_list) > 0:
            log.warning("You have commits not pushed on {} repo", path)
        else:
            log.debug("You pushed all commits on {} repo", path)
        for c in commits_ahead_list:
            message = str(c.message).strip().replace("\n", "")

            sha = c.hexsha[0:7]
            if len(message) > 60:  # pragma: no cover
                message = message[0:57] + "..."
            log.warning("Unpushed commit in {}: {} ({})", path, sha, message)


def get_last_commit(gitobj: Repo) -> str:
    if gitobj and gitobj.heads:
        return next(gitobj.iter_commits()).hexsha[0:8]
    return ""
