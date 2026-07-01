from __future__ import annotations

import re
from typing import Any

from hiddifypanel.models import ConfigEnum, hconfig

from hiddifypanel import hutils

AUTO_CLIENT_CORE_PRIORITY: tuple[str, ...] = ('hiddify-core', 'singbox', 'xray', 'sublink')


def resolve_auto_client_cores(user_agent: str, ua_parsed: dict[str, Any], child_id: int = 0) -> list[str]:
    """Return client core names that would be auto-selected for a subscription User-Agent."""
    if ua_parsed.get('is_browser'):
        return []

    ua = user_agent or ''
    if ua_parsed.get('is_singbox') or re.match(r'^(HiddifyNext|Dart|SFI|SFA)', ua, re.IGNORECASE):
        return ['hiddify-core', 'singbox']

    if re.match(r'^(Clash-verge|Clash-?Meta|Stash|NekoBox|NekoRay|Pharos|hiddify-desktop)', ua, re.IGNORECASE):
        return ['clash']
    if re.match(r'^(Clash|Stash)', ua, re.IGNORECASE):
        return ['clash']

    if hconfig(ConfigEnum.sub_full_xray_json_enable, child_id):
        if ua_parsed.get('is_v2rayng') and hutils.flask.is_client_version(
            hutils.flask.ClientVersion.v2ryang, 1, 8, 17
        ):
            return ['xray']
        if ua_parsed.get('is_streisand'):
            return ['xray']

    if re.match(
        r'^(Hiddify|FoXray|Fair|v2rayNG|SagerNet|Shadowrocket|V2Box|Loon|Liberty|Streisand)',
        ua,
        re.IGNORECASE,
    ):
        return ['sublink']

    return []


def _priority_core(name: str, child_id: int) -> bool:
    if name == 'xray' and not hconfig(ConfigEnum.sub_full_xray_json_enable, child_id):
        return False
    return True


def resolve_default_client_core(configured_cores: list[str], child_id: int = 0) -> str | None:
    """First configured client core in auto-selection priority order."""
    configured = {str(c).strip() for c in configured_cores if str(c).strip()}
    for name in AUTO_CLIENT_CORE_PRIORITY:
        if name in configured and _priority_core(name, child_id):
            return name
    for name in configured_cores:
        core = str(name).strip()
        if core:
            return core
    return None


def resolve_primary_auto_client_core(
    user_agent: str,
    ua_parsed: dict[str, Any],
    child_id: int,
    configured_cores: list[str],
) -> str | None:
    """Single auto client core: highest-priority match between UA and configured cores."""
    auto_cores = set(resolve_auto_client_cores(user_agent, ua_parsed, child_id))
    if not auto_cores:
        return None
    configured = {str(c).strip() for c in configured_cores if str(c).strip()}
    for name in AUTO_CLIENT_CORE_PRIORITY:
        if name in configured and name in auto_cores and _priority_core(name, child_id):
            return name
    for name in AUTO_CLIENT_CORE_PRIORITY:
        if name in auto_cores and _priority_core(name, child_id):
            return name
    return next(iter(auto_cores), None)
