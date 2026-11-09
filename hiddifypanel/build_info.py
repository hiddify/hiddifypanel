"""Which commit a development (unreleased) panel was installed from, for the version shown in the admin UI."""

import re
import subprocess
from datetime import UTC, datetime
from functools import cache
from pathlib import Path
from typing import NamedTuple

_PACKAGE_DIR = Path(__file__).resolve().parent
# Written by the manager's installer (scripts/common/utils.sh, write_panel_commit); not tracked in git.
# Its hash, then its version.
_COMMIT_FILE = _PACKAGE_DIR / "COMMIT"
_SHORT = 7
_HASH = re.compile(r"[0-9a-f]{7,40}")
# The development version of a commit, as the manager's get_commit_version gives it: MM-DDTHH:MM of its commit date in
# UTC (its update check compares it with the installed one).
_VERSION = re.compile(r"\d{2}-\d{2}T\d{2}:\d{2}")
_VERSION_FORMAT = "%m-%dT%H:%M"


class BuildCommit(NamedTuple):
    commit: str = ""  # short hash
    version: str = ""  # MM-DDTHH:MM (UTC)


def _git(*args: str) -> str:
    # The installer gives the checkout to the panel's user while its git directory stays root's, which git refuses as
    # "dubious ownership"; trusting it here is safe, as both owners are the panel's user and root.
    try:
        out = subprocess.run(
            ["git", "-c", f"safe.directory={_PACKAGE_DIR.parent}", "-C", str(_PACKAGE_DIR), *args],
            capture_output=True,
            text=True,
            timeout=3,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return ""
    return out.stdout if out.returncode == 0 else ""


def _from_git() -> tuple[str, str]:
    """(hash, version) of HEAD of the panel's own checkout (an editable install), or empty.

    Only when the package sits at the top of that checkout: an installed package lives under the manager's
    directory, which is a git checkout itself, and its commit is not the panel's.
    """
    top = _git("rev-parse", "--show-toplevel").strip()
    if not top or Path(top).resolve() != _PACKAGE_DIR.parent:
        return "", ""
    fields = _git("show", "-s", "--format=%H %ct", "HEAD").split()
    if len(fields) != 2 or not fields[1].isdigit():
        return "", ""
    return fields[0], datetime.fromtimestamp(int(fields[1]), UTC).strftime(_VERSION_FORMAT)


def _from_file() -> tuple[str, str]:
    try:
        lines = _COMMIT_FILE.read_text(encoding="utf-8").split()
    except OSError:
        return "", ""
    return (lines + ["", ""])[0], (lines + ["", ""])[1]


@cache
def build_commit() -> BuildCommit:
    """The commit of this build, empty fields where unknown.

    The file first: whoever installed or copied this tree wrote it, while a checkout's git can be older than the
    files in it (a tree copied over without its .git). Read once per process: the panel restarts when its code
    changes.
    """
    for source in (_from_file, _from_git):
        commit, version = source()
        commit = commit.lower()
        if _HASH.fullmatch(commit):
            return BuildCommit(commit[:_SHORT], version if _VERSION.fullmatch(version) else "")
    return BuildCommit()


def dev_version_label() -> str:
    """"DEV 11-09T19:14 · 1a2b3c4" (each part only when known), for a development panel."""
    info = build_commit()
    return " ".join(["DEV", " · ".join(p for p in (info.version, info.commit) if p)]).strip()
