"""The bot's texts: keys are a ``StrEnum`` (a typo is an error, not a silent blank), strings live in
``translations.i18n/<lang>.json`` under ``bot``, English as fallback."""

import json
from enum import StrEnum
from functools import cache
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[3] / "translations.i18n"


class T(StrEnum):
    # common
    back = "back"
    menu = "menu"
    refresh = "refresh"
    close = "close"
    cancel = "cancel"
    confirm = "confirm"
    done = "done"
    not_allowed = "not_allowed"
    gone = "gone"
    read_only_node = "read_only_node"
    unknown = "unknown"
    # user side
    welcome = "welcome"
    linked = "linked"
    account_title = "account_title"
    status_active = "status_active"
    status_disabled = "status_disabled"
    status_expired = "status_expired"
    status_no_data = "status_no_data"
    days_left = "days_left"
    days_not_started = "days_not_started"
    days_expired = "days_expired"
    last_online = "last_online"
    never = "never"
    online_now = "online_now"
    ago_minutes = "ago_minutes"
    ago_hours = "ago_hours"
    ago_days = "ago_days"
    resets_in = "resets_in"
    links = "links"
    data = "data"
    time = "time"
    used_of = "used_of"
    manage = "manage"
    updated = "updated"
    sending = "sending"
    links_title = "links_title"
    link_home = "link_home"
    link_sub = "link_sub"
    link_hiddify = "link_hiddify"
    links_hint = "links_hint"
    qr = "qr"
    my_page = "my_page"
    # admin home
    admin_hello = "admin_hello"
    admin_summary = "admin_summary"
    btn_users = "btn_users"
    btn_new = "btn_new"
    btn_status = "btn_status"
    btn_check = "btn_check"
    btn_backup = "btn_backup"
    btn_panel = "btn_panel"
    panel = "panel"
    # users list
    users_title = "users_title"
    users_empty = "users_empty"
    users_count = "users_count"
    f_all = "f_all"
    f_active = "f_active"
    f_expiring = "f_expiring"
    f_ended = "f_ended"
    f_online = "f_online"
    search = "search"
    search_prompt = "search_prompt"
    search_results = "search_results"
    search_clear = "search_clear"
    # user card
    owner = "owner"
    renew = "renew"
    renewed = "renewed"
    add_days = "add_days"
    add_gb = "add_gb"
    added_days = "added_days"
    added_gb = "added_gb"
    reset_usage = "reset_usage"
    usage_reset = "usage_reset"
    enable = "enable"
    disable = "disable"
    enabled = "enabled"
    disabled = "disabled"
    delete = "delete"
    delete_confirm = "delete_confirm"
    deleted = "deleted"
    last_user = "last_user"
    limit_reached = "limit_reached"
    pick_days = "pick_days"
    pick_gb = "pick_gb"
    # create
    new_title = "new_title"
    new_gb = "new_gb"
    new_days = "new_days"
    new_count = "new_count"
    new_name = "new_name"
    new_name_prompt = "new_name_prompt"
    new_summary = "new_summary"
    new_create = "new_create"
    new_working = "new_working"
    new_done_one = "new_done_one"
    new_done_many = "new_done_many"
    # status
    status_title = "status_title"
    cpu = "cpu"
    ram = "ram"
    disk = "disk"
    uptime = "uptime"
    users_block = "users_block"
    traffic = "traffic"
    traffic_today = "traffic_today"
    traffic_yesterday = "traffic_yesterday"
    traffic_week = "traffic_week"
    traffic_month = "traffic_month"
    traffic_total = "traffic_total"
    users_line = "users_line"
    online_line = "online_line"
    updated_at = "updated_at"
    # backup
    backup_working = "backup_working"
    backup_caption = "backup_caption"
    backup_failed = "backup_failed"
    # notifications
    notify_days = "notify_days"
    notify_data = "notify_data"
    notify_admin = "notify_admin"
    notify_admin_line = "notify_admin_line"
    notify_admin_more = "notify_admin_more"
    # units
    gb = "gb"
    unit_d = "unit_d"
    unit_h = "unit_h"
    unit_m = "unit_m"


@cache
def _table(lang: str) -> dict[str, str]:
    def load(code: str) -> dict[str, str]:
        try:
            section = json.loads((_ROOT / f"{code}.json").read_text(encoding="utf-8")).get("bot", {})
        except (OSError, ValueError):
            return {}
        return {k: v for k, v in section.items() if isinstance(v, str) and v}

    return {**load("en"), **load(lang)} if lang != "en" else load("en")


def t(key: T, lang: str, /, **values: object) -> str:
    """The text for ``key`` in ``lang``, with ``{name}`` placeholders filled from ``values``."""
    text = _table(lang).get(key.value, key.value)
    return text.format(**values) if values else text
