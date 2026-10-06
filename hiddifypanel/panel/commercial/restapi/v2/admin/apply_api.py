"""Apply page API (admin v2, super admins): apply configs, reinstall, update, restart and check status,
with the run's live progress read from its log.

The scripts write ``####percent####title####text####`` lines into ``data/log/system/<name>.log`` and end with
``----Finished!----``; ``GET apply/log/`` hands the page what is new since its last read, plus the parsed progress.
"""

from __future__ import annotations

import fcntl
import os
import re
import subprocess
import time
from pathlib import Path
from typing import Any

from apiflask import abort
from flask import request
from flask.views import MethodView
from loguru import logger

from hiddifypanel import g, hutils
from hiddifypanel.auth import login_required
from hiddifypanel.models import ConfigEnum, Role, hconfig
from hiddifypanel.panel.run_commander import Command, commander

ROLES = {Role.super_admin}
LOG_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
PROGRESS_RE = re.compile(r"####(\d+)####(.*?)####(.*?)####")
FINISHED_MARK = "Finished!"
MAX_CHUNK = 256 * 1024
TAIL_DEFAULT = 64 * 1024

#: action key → (command, log file, systemd unit that runs it, what the run is)
ACTIONS: dict[str, dict[str, Any]] = {  # "lock": the installer lock the run holds
    "apply": {"command": Command.apply, "log": "0-install.log", "unit": "hiddify-apply", "lock": "0-install"},
    "install": {"command": Command.install, "log": "0-install.log", "unit": "hiddify-install", "lock": "0-install"},
    "update": {"command": Command.update, "log": "update.log", "unit": "hiddify-update", "lock": None},
    "restart": {"command": Command.restart_services, "log": "restart.log", "unit": None, "lock": None},
    "status": {"command": Command.status, "log": "status.log", "unit": None, "lock": None},
}


def log_dir() -> Path:
    return Path(os.environ.get("HIDDIFY_CONFIG_PATH", "/opt/hiddify-manager/")) / "data" / "log" / "system"


def _lock_held(name: str) -> bool:
    """Is the installer's flock (``scripts/common/utils.sh`` set_lock) held right now?"""
    path = Path(os.environ.get("HIDDIFY_LOCKS") or Path(os.environ.get("HIDDIFY_CONFIG_PATH", "/opt/hiddify-manager/")) / "data" / "locks") / f"{name}.lock"
    try:
        fd = os.open(path, os.O_RDONLY)
    except OSError:
        return False
    try:
        fcntl.flock(fd, fcntl.LOCK_SH | fcntl.LOCK_NB)
        fcntl.flock(fd, fcntl.LOCK_UN)
        return False
    except OSError:
        return True
    finally:
        os.close(fd)


def _unit_active(unit: str | None) -> bool:
    if not unit:
        return False
    try:
        return subprocess.run(["systemctl", "is-active", "--quiet", f"{unit}.service"], check=False, timeout=5).returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def running_actions() -> list[str]:
    """Actions running now: their systemd unit is active, or (started from the console) the installer lock is held."""
    out = [key for key, spec in ACTIONS.items() if _unit_active(spec["unit"])]
    if not {"apply", "install"} & set(out) and _lock_held("0-install"):
        out.append("install")
    return out


def _log_path(name: str) -> Path:
    if not name or not LOG_NAME_RE.match(name):
        abort(400, "Invalid log file")
    root = log_dir().resolve()
    path = (root / os.path.basename(name)).resolve()
    if path.parent != root or not path.is_file():
        abort(404, "Log file not found")
    return path


def _log_files() -> list[dict[str, Any]]:
    root = log_dir()
    if not root.is_dir():
        return []
    rows = []
    for p in root.iterdir():
        if p.is_file() and LOG_NAME_RE.match(p.name):
            st = p.stat()
            rows.append({"name": p.name, "size": st.st_size, "mtime": st.st_mtime})
    return sorted(rows, key=lambda r: -r["mtime"])


def _last_runs() -> dict[str, dict[str, Any]]:
    """When each action last ran and whether it finished (from the end of its log)."""
    out = {}
    for key, spec in ACTIONS.items():
        path = log_dir() / spec["log"]
        if not path.is_file():
            continue
        st = path.stat()
        tail = _read_tail(path, 4096)
        out[key] = {"mtime": st.st_mtime, "finished": FINISHED_MARK in tail}
    return out


def _read_tail(path: Path, size: int) -> str:
    with path.open("rb") as fh:
        fh.seek(0, os.SEEK_END)
        end = fh.tell()
        fh.seek(max(0, end - size))
        return fh.read().decode("utf-8", errors="replace")


def _strip_progress(text: str) -> str:
    """The log without the machine-readable progress lines."""
    return "\n".join(line for line in text.split("\n") if not PROGRESS_RE.fullmatch(line.strip()))


def _api_bases() -> list[str]:
    """Where the page can poll the log: the current admin path, and the new one if it just changed.

    While apply/install runs after a proxy_path change, the new path only routes once nginx is regenerated
    and the old one stops once the panel restarts, so the page tries both (as the classic result page does).
    """
    current = f"/{g.proxy_path}/api/v2/admin/"
    new = f"/{hconfig(ConfigEnum.proxy_path_admin)}/api/v2/admin/"
    return list(dict.fromkeys([new, current]))


def _domains() -> list[str]:
    """Every domain of the panel: after a domain change, only some of them answer (and which ones changes mid-run)."""
    from hiddifypanel.models import Domain

    out = []
    for d in Domain.get_domains(always_add_all_domains=True, always_add_ip=False):
        name = str(d.domain or "").replace("*", hutils.random.get_random_string(3, 6))
        if name and name not in out:
            out.append(name)
    return out


def log_sources() -> dict[str, Any]:
    """What the page needs to keep reading the log through path and domain changes."""
    return {"api_bases": _api_bases(), "domains": _domains(), "api_key": g.account.uuid, "admin_links": _admin_links()}


def _admin_links() -> list[str]:
    """The panel's admin link on each domain: after a domain or path change these are the new addresses."""
    from hiddifypanel.panel import hiddify

    out = []
    for name in _domains():
        try:
            out.append(hiddify.get_account_panel_link(g.account, name))
        except Exception:
            continue
    return out[:8]


def _state() -> dict[str, Any]:
    return {
        "running": running_actions(),
        "last": _last_runs(),
        "files": _log_files(),
        "node": bool(hutils.node.is_child()),
        "now": time.time(),
        **log_sources(),
    }


def _cors(payload: dict, preflight: bool = False):
    """JSON with the CORS headers the classic log API sends (the API key header carries the login)."""
    from flask import jsonify

    resp = jsonify(payload)
    resp.headers["Cache-Control"] = "no-store"
    resp.headers["Access-Control-Allow-Origin"] = "*"
    if preflight:
        resp.headers["Allow"] = "GET, OPTIONS"
        resp.headers["Access-Control-Allow-Headers"] = "Hiddify-API-Key"
        resp.headers["Access-Control-Allow-Methods"] = "GET, OPTIONS"
    return resp


class ApplyApi(MethodView):
    decorators = [login_required(ROLES)]

    def get(self):
        """Apply page: what is running, when each action last ran, and the log files"""
        return _state()


def check_can_start(action: str) -> None:
    """Aborts (409 / 400) when ``action`` can not be started now."""
    if action not in ACTIONS:
        abort(404, "Unknown action")
    if action in ("apply", "install", "update") and running_actions():
        abort(409, "Another action is still running")
    if action in ("apply", "install") and int(hconfig(ConfigEnum.db_version)) < 9:
        abort(400, "Please update your panel before this action.")


def start_action(action: str) -> dict[str, Any]:
    """Start an action (the Apply page, and the restore that reinstalls afterwards); the page then follows its log."""
    check_can_start(action)
    spec = ACTIONS[action]
    if action in ("apply", "install") and hutils.node.is_child():
        hutils.node.run_node_op_in_bg(hutils.node.child.sync_with_parent)
    started = time.time()
    try:
        commander(spec["command"])
    except Exception as e:
        logger.exception(e)
        abort(500, "Could not start the action")
    return {"action": action, "log": spec["log"], "started": started, **_state()}


class ApplyActionApi(MethodView):
    decorators = [login_required(ROLES)]

    def post(self, action: str):
        """Start an action (apply configs, reinstall, update, restart, status)"""
        return start_action(action)


class ApplyLogApi(MethodView):
    decorators = [login_required(ROLES)]

    def get(self):
        """New log text since ``offset`` (``tail=1``: the end of the file), with the parsed progress"""
        path = _log_path(request.args.get("file", ""))
        offset = request.args.get("offset", default=0, type=int)
        since = request.args.get("since", default=0.0, type=float)
        st = path.stat()
        size = st.st_size
        # A log older than this run is the previous run's (it still ends in "Finished!").
        if since and st.st_mtime < since - 1:
            return _cors({"text": "", "offset": 0, "size": size, "mtime": st.st_mtime, "started": False, "progress": None, "finished": False, "reset": True})

        reset = False
        if request.args.get("tail"):
            offset = max(0, size - TAIL_DEFAULT)
        elif offset > size or offset < 0:  # truncated: a new run began
            offset = 0
            reset = True
        with path.open("rb") as fh:
            fh.seek(offset)
            raw = fh.read(MAX_CHUNK)
        end = offset + len(raw)
        text = raw.decode("utf-8", errors="replace")
        tail = _read_tail(path, 64 * 1024)
        matches = PROGRESS_RE.findall(tail)
        progress = None
        if matches:
            percent, title, sub = matches[-1]
            progress = {"percent": int(percent), "title": title.strip(), "text": sub.strip()}
        finished = FINISHED_MARK in tail[-4096:]
        return _cors(
            {
                "text": _strip_progress(text),
                "offset": end,
                "size": size,
                "mtime": st.st_mtime,
                "started": True,
                "progress": progress,
                "finished": finished,
                "reset": reset,
            }
        )

    def options(self):
        """CORS preflight: the page may read the log through another of the panel's domains."""
        if g.proxy_path != hconfig(ConfigEnum.proxy_path_admin):
            abort(403)
        return _cors({}, preflight=True)


def _clear(path: Path) -> bool:
    """Empty a log in place (the writers keep their file). False when the file can not be written."""
    try:
        with path.open("r+b") as fh:
            fh.truncate(0)
        return True
    except OSError as e:
        logger.warning(f"Could not clear {path.name}: {e}")
        return False


def _logs_in_use() -> set[str]:
    return {ACTIONS[key]["log"] for key in running_actions()}


class ApplyLogClearApi(MethodView):
    decorators = [login_required(ROLES)]

    def delete(self, name: str):
        """Empty one log file"""
        path = _log_path(name)
        if path.name in _logs_in_use():
            abort(409, "This log is being written by a running action")
        if not _clear(path):
            abort(500, "Could not clear the log")
        return {"cleared": 1, "files": _log_files()}


class ApplyLogsClearApi(MethodView):
    decorators = [login_required(ROLES)]

    def post(self):
        """Empty every log file (the log of a running action is left alone)"""
        busy = _logs_in_use()
        cleared, failed, skipped = 0, [], []
        for f in _log_files():
            if f["name"] in busy:
                skipped.append(f["name"])
            elif f["size"] == 0 or _clear(_log_path(f["name"])):
                cleared += f["size"] > 0
            else:
                failed.append(f["name"])
        return {"cleared": cleared, "failed": failed, "skipped": skipped, "files": _log_files()}


class ApplyLogDownloadApi(MethodView):
    decorators = [login_required(ROLES)]

    def get(self, name: str):
        """Download a whole log file"""
        from flask import Response

        path = _log_path(name)
        text = re.sub(r"\x1b\[[0-9;]*[A-Za-z]", "", path.read_text(encoding="utf-8", errors="replace"))
        resp = Response(_strip_progress(text), mimetype="text/plain")
        resp.headers["Content-Disposition"] = f'attachment; filename="{path.name}"'
        resp.headers["Cache-Control"] = "no-store"
        return resp
