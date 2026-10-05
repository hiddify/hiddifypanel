"""Backup page API (admin v2, super admins): download a backup, the server's automatic backups, and restore.

Restoring is two steps: ``POST backup/restore/`` checks the backup and keeps it (with the chosen parts)
under a one-time token; the page then opens ``admin.Backup:restore_run`` in the action dialog, which
restores and runs the reinstall with its live log in the same request (the admin path may change).
"""

from __future__ import annotations

import datetime
import gzip
import io
import json
import os
import re
import secrets
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from apiflask import abort
from flask import Response, request
from flask.views import MethodView
from loguru import logger

from hiddifypanel import g
from hiddifypanel.auth import login_required
from hiddifypanel.database import db
from hiddifypanel.hutils.flask import hurl_for
from hiddifypanel.models import AdminUser, Child, ConfigEnum, CustomProxy, Domain, Role, User, hconfig
from hiddifypanel.panel import hiddify

#: Automatic backups: ``YYYY_MM_DD__HH_MM_SS.json`` (panel/cli.py backup_task).
FILE_RE = re.compile(r"^\d{4}_\d{2}_\d{2}__\d{2}_\d{2}_\d{2}\.json$")
RESTORE_TTL = 15 * 60
#: Uploads come gzipped (the admin path accepts 10 MB); this caps what they may unpack to.
MAX_BACKUP_BYTES = 512 * 1024 * 1024
#: Sections a valid backup has (older ones may miss the newer optional ones).
REQUIRED_KEYS = ("admin_users",)


def backup_dir() -> Path:
    return Path(os.environ.get("HIDDIFY_CONFIG_PATH", "/opt/hiddify-manager/")) / "data" / "backup"


def summarize(data: dict) -> dict[str, Any]:
    """What a backup holds (counts per part) and what restoring it would change."""
    # The main panel's settings (the first child in the backup; nodes have their own).
    childs = data.get("childs") or []
    root = childs[0].get("unique_id") if childs and isinstance(childs[0], dict) else None
    configs = {c.get("key"): c.get("value") for c in data.get("hconfigs") or [] if isinstance(c, dict) and (root is None or c.get("child_unique_id") in (root, None))}
    admin_path = configs.get("proxy_path_admin")
    return {
        "users": len(data.get("users") or []),
        "admins": len(data.get("admin_users") or []),
        "domains": len(data.get("domains") or []),
        "custom_proxies": len(data.get("custom_proxies") or []),
        "tags": len(data.get("tags") or []),
        "settings": len(data.get("hconfigs") or []),
        "nodes": max(0, len(data.get("childs") or []) - 1),
        "domain_names": [d.get("domain") for d in (data.get("domains") or [])[:6] if isinstance(d, dict) and d.get("domain")],
        # The admin link changes when settings are restored from another panel.
        "admin_path_changes": bool(admin_path) and admin_path != hconfig(ConfigEnum.proxy_path_admin),
    }


def current_summary() -> dict[str, Any]:
    return {
        "users": User.query.count(),
        "admins": AdminUser.query.count(),
        "domains": Domain.query.count(),
        "custom_proxies": CustomProxy.query.count(),
        "nodes": max(0, Child.query.count() - 1),
    }


def _file_row(path: Path) -> dict[str, Any]:
    stat = path.stat()
    # When it was written, with its timezone (the name is in the server's local time).
    created = datetime.datetime.fromtimestamp(stat.st_mtime, tz=datetime.timezone.utc).isoformat()
    return {"name": path.name, "size": stat.st_size, "created": created}


def list_files() -> list[dict[str, Any]]:
    root = backup_dir()
    if not root.is_dir():
        return []
    rows = [_file_row(p) for p in root.iterdir() if p.is_file() and FILE_RE.match(p.name)]
    return sorted(rows, key=lambda r: r["created"], reverse=True)


def _file(name: str) -> Path:
    if not FILE_RE.match(name or ""):
        abort(400, "Invalid backup name")
    path = backup_dir() / name
    if not path.is_file():
        abort(404, "Backup not found")
    return path


def _read_backup(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        abort(400, "This backup file can not be read")
    return data


def check_backup(data: Any) -> dict:
    if not isinstance(data, dict) or any(k not in data for k in REQUIRED_KEYS):
        abort(400, "This is not a Hiddify backup file")
    return data


def read_body() -> dict:
    """The request's JSON; a gzipped body (``Content-Type: application/gzip``) is unpacked first."""
    if request.mimetype == "application/gzip":
        out = io.BytesIO()
        try:
            with gzip.GzipFile(fileobj=io.BytesIO(request.get_data())) as fh:
                while chunk := fh.read(1 << 20):
                    out.write(chunk)
                    if out.tell() > MAX_BACKUP_BYTES:
                        abort(413, "This backup is too large")
            body = json.loads(out.getvalue())
        except (OSError, EOFError, ValueError):
            abort(400, "This backup file can not be read")
        return body if isinstance(body, dict) else {}
    return request.get_json(silent=True) or {}


def _download_name() -> str:
    host = urlparse(request.base_url).hostname or "panel"
    return f"hiddify-{host}-{datetime.datetime.now().strftime('%Y-%m-%d_%H-%M')}.json"


def _json_attachment(text: str, filename: str) -> Response:
    resp = Response(text, mimetype="application/json")
    resp.headers["Content-Disposition"] = f'attachment; filename="{filename}"'
    resp.headers["Cache-Control"] = "no-store"
    return resp


def write_backup_file() -> Path:
    """Same file the automatic (cron) backups write; readable by the panel user only."""
    root = backup_dir()
    root.mkdir(mode=0o750, parents=True, exist_ok=True)
    dst = root / f"{datetime.datetime.now().strftime('%Y_%m_%d__%H_%M_%S')}.json"
    fd = os.open(dst, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o640)
    with os.fdopen(fd, "w", encoding="utf-8") as fp:
        json.dump(hiddify.dump_db_to_dict(), fp, indent=2, sort_keys=True, default=str)
    return dst


def _telegram() -> dict[str, Any]:
    bot = getattr(g, "bot", None)
    return {"bot": bool(bot and getattr(bot, "username", None)), "connected": bool(g.account.telegram_id)}


def _state() -> dict[str, Any]:
    return {"current": current_summary(), "files": list_files(), "telegram": _telegram(), "directory": str(backup_dir())}


# ---------------------------------------------------------------------------------------------- restore token


def _restore_key(token: str) -> str:
    return f"backup-restore:{token}"


def stash_restore(data: dict, options: dict[str, bool]) -> str:
    from hiddifypanel.cache import redis_client

    token = secrets.token_urlsafe(24)
    payload = {"admin": g.account.uuid, "options": options, "data": data}
    redis_client.set(_restore_key(token), gzip.compress(json.dumps(payload, default=str).encode()), ex=RESTORE_TTL)
    return token


def take_restore(token: str) -> dict | None:
    """The stashed restore, once (deleted when read), and only for the admin who prepared it."""
    from hiddifypanel.cache import redis_client

    if not re.fullmatch(r"[\w-]{20,64}", token or ""):
        return None
    key = _restore_key(token)
    raw = redis_client.get(key)
    redis_client.delete(key)
    if not raw:
        return None
    payload = json.loads(gzip.decompress(raw))
    if payload.get("admin") != g.account.uuid:
        return None
    return payload


# ---------------------------------------------------------------------------------------------- views


class BackupApi(MethodView):
    decorators = [login_required({Role.super_admin})]

    def get(self):
        """Backup page: what the panel has now, the server's automatic backups, Telegram delivery"""
        return _state()


class BackupDownloadApi(MethodView):
    decorators = [login_required({Role.super_admin})]

    def get(self):
        """Download a backup of the panel as it is now (JSON)"""
        return _json_attachment(json.dumps(hiddify.dump_db_to_dict(), indent=2, default=str), _download_name())


class BackupFilesApi(MethodView):
    decorators = [login_required({Role.super_admin})]

    def post(self):
        """Make a backup on the server now (kept with the automatic ones)"""
        path = write_backup_file()
        return {"created": path.name, **_state()}


class BackupFileApi(MethodView):
    decorators = [login_required({Role.super_admin})]

    def get(self, name: str):
        """Download one of the server's backups (``?summary=1``: only what it holds)"""
        path = _file(name)
        if request.args.get("summary"):
            return summarize(check_backup(_read_backup(path)))
        return _json_attachment(path.read_text(encoding="utf-8"), f"hiddify-{name}")

    def delete(self, name: str):
        """Delete one of the server's backups"""
        _file(name).unlink()
        return _state()


class BackupRestoreApi(MethodView):
    decorators = [login_required({Role.super_admin})]

    def post(self):
        """Prepare a restore (an uploaded backup or a server one) and return the page that runs it"""
        body = read_body()
        if body.get("file"):
            data = check_backup(_read_backup(_file(str(body["file"]))))
        else:
            data = check_backup(body.get("data"))
        summary = summarize(data)
        if body.get("dry_run"):
            return {"summary": summary}
        options = {k: bool(body.get(k)) for k in ("settings", "users", "domains", "replace_owner_admin")}
        if not (options["settings"] or options["users"] or options["domains"]):
            abort(400, "Choose at least one part to restore")
        try:
            token = stash_restore(data, options)
        except Exception as e:
            logger.exception(e)
            abort(500, "Could not prepare the restore")
        return {"summary": summary, "run_url": hurl_for("admin.Backup:restore_run", token=token)}


def run_restore(payload: dict) -> None:
    """Restore exactly like the classic Backup page."""
    from hiddifypanel.models import set_hconfig

    options = payload["options"]
    set_hconfig(ConfigEnum.first_setup, False)
    hiddify.set_db_from_json(
        payload["data"],
        set_users=options.get("users", False),
        set_domains=options.get("domains", False),
        set_settings=options.get("settings", False),
        override_unique_id=False,
        override_child_unique_id=True,
        replace_owner_admin=options.get("replace_owner_admin", False),
    )
    db.session.commit()
