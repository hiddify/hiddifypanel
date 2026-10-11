"""Outbound manager: built-in defaults, upgrade sync, validation and the routing data for server templates.

Defaults live in ``proxy_templates/outbounds/defaults.yaml``. Built-in outbounds (WARP, Direct, Block)
keep a copy of the file's lists in ``builtin_lists``; while the admin has not edited the lists
(``lists_override`` off) each sync replaces them with the file's, so upgrades bring new sites.
"""

from __future__ import annotations

import hashlib
import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from loguru import logger
from pydantic import BaseModel, Field

from hiddifypanel.database import db
from hiddifypanel.models.external_model.outbound import OutboundModel
from hiddifypanel.models.outbound import (
    BUILTIN_MODES,
    CONFIGURABLE_ENDPOINT_MODES,
    CUSTOM_CONFIG_MODES,
    ENDPOINT_MODES,
    LIST_FIELDS,
    MULTI_MODES,
    RULE_ORDER,
    Outbound,
    OutboundMode,
)
from hiddifypanel.proxy_v3 import outbound_custom as custom_config

DEFAULTS_FILE = Path(__file__).resolve().parent / "proxy_templates" / "outbounds" / "defaults.yaml"

SING_GEOSITE_URL = "https://raw.githubusercontent.com/SagerNet/sing-geosite/rule-set/{name}.srs"
SING_GEOIP_URL = "https://raw.githubusercontent.com/SagerNet/sing-geoip/rule-set/{name}.srs"

#: Region of the panel (hconfig ``country``), as the route templates used before the outbound manager.
REGION_BY_COUNTRY = {"zh": "cn", "cn": "cn", "ir": "ir", "ru": "ru"}

_DOMAIN_RE = re.compile(r"^(?=.{1,253}$)(?!-)[a-z0-9-]{1,63}(?<!-)(\.(?!-)[a-z0-9-]{1,63}(?<!-))*$")
#: xray: geosite:<tag> (domain rule) or geoip:<code> (ip rule); attributes like geosite:google@ads are fine.
_GEOSITE_RE = re.compile(r"^(geosite|geoip):!?[a-z0-9][a-z0-9_.!@-]*$")
_RULE_SET_NAME_RE = re.compile(r"^geo(site|ip)-[a-z0-9][a-z0-9_.@!-]*$")
_RULE_SET_URL_RE = re.compile(r"^https?://[^\s/]+/\S+\.(srs|json)$", re.IGNORECASE)


# --------------------------------------------------------------------------- defaults file


def _defaults_key() -> tuple[str, float]:
    try:
        return str(DEFAULTS_FILE), DEFAULTS_FILE.stat().st_mtime
    except OSError:
        return str(DEFAULTS_FILE), 0.0


@lru_cache(maxsize=4)
def _load_defaults_cached(_key: tuple[str, float]) -> dict[str, Any]:
    try:
        data = yaml.safe_load(DEFAULTS_FILE.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError) as e:
        logger.error(f"Outbound defaults could not be read ({DEFAULTS_FILE}): {e}")
        data = {}
    return data if isinstance(data, dict) else {}


def load_defaults() -> dict[str, Any]:
    """The parsed defaults file (re-read when it changes)."""
    return _load_defaults_cached(_defaults_key())


def default_endpoint(mode: OutboundMode | str) -> dict[str, Any]:
    return dict((load_defaults().get("endpoints") or {}).get(str(mode)) or {})


def _builtin_spec(mode: OutboundMode) -> dict[str, Any]:
    spec = (load_defaults().get("outbounds") or {}).get(str(mode)) or {}
    lists = {field: clean_list(field, spec.get(field) or []) for field in LIST_FIELDS}
    lists["domestic"] = bool(spec.get("domestic", False))
    return {"name": str(spec.get("name") or str(mode).title()), "default": bool(spec.get("default", False)), "lists": lists}


# --------------------------------------------------------------------------- list cleaning / validation


def _clean_site(value: str) -> str:
    site = value.strip().lower()
    for prefix in ("https://", "http://", "domain:", "full:"):
        if site.startswith(prefix):
            site = site[len(prefix) :]
    site = site.split("/", 1)[0].split(":", 1)[0].strip(".")
    return site[2:] if site.startswith("*.") else site


def _clean_geosite(value: str) -> str:
    """xray entries keep their prefix; a bare name is a geosite."""
    tag = value.strip().lower().replace(" ", "")
    return tag if tag.startswith(("geosite:", "geoip:")) or not tag else f"geosite:{tag}"


def rule_set_url(item: str) -> str:
    """A rule-set URL; a bare SagerNet name (``geosite-netflix``, ``geoip-ir``) becomes its URL."""
    item = item.strip()
    if item.lower().startswith(("http://", "https://")):
        return item
    name = item.lower().removesuffix(".srs")
    if _RULE_SET_NAME_RE.match(name):
        return (SING_GEOIP_URL if name.startswith("geoip-") else SING_GEOSITE_URL).format(name=name)
    return item  # left as typed: rejected by invalid_entries


def _clean_rule_set(value: str) -> str:
    return rule_set_url(value)


_CLEANERS = {"sites": _clean_site, "geosites": _clean_geosite, "rule_sets": _clean_rule_set}


def clean_list(field: str, values: Any) -> list[str]:
    """Trimmed, prefix-free, de-duplicated entries (order kept). Accepts a list or newline/comma text."""
    if isinstance(values, str):
        values = re.split(r"[\n,]+", values)
    out: list[str] = []
    for raw in values or []:
        item = _CLEANERS[field](str(raw))
        if item and item not in out:
            out.append(item)
    return out


def invalid_entries(field: str, values: list[str]) -> list[str]:
    """Entries that would break the generated config."""
    if field == "sites":
        return [v for v in values if not _DOMAIN_RE.match(v)]
    if field == "geosites":
        return [v for v in values if not _GEOSITE_RE.match(v)]
    return [v for v in values if not _RULE_SET_URL_RE.match(v)]


# --------------------------------------------------------------------------- built-in rows / sync


def _apply_lists(row: Outbound, lists: dict[str, Any]) -> None:
    for field in LIST_FIELDS:
        setattr(row, field, list(lists.get(field) or []))
    row.domestic = bool(lists.get("domestic", False))


def current_lists(row: Outbound) -> dict[str, Any]:
    out: dict[str, Any] = {field: list(getattr(row, field) or []) for field in LIST_FIELDS}
    out["domestic"] = bool(row.domestic)
    return out


class OutboundOrderError(ValueError):
    """An order / enabled state the routing can not use (shown to the admin as is)."""


def has_rules(row: Outbound) -> bool:
    return bool(row.domestic or row.sites or row.geosites or row.rule_sets)


def ordered_rows(child_id: int = 0) -> list[Outbound]:
    """All outbounds in rule order (``child_id`` is kept for callers; the outbounds are shared by all nodes)."""
    rows = Outbound.query.all()
    return sorted(rows, key=lambda r: (r.position or 0, r.id or 0))


def default_row(rows: list[Outbound]) -> Outbound | None:
    """The default outbound: the last enabled one (rows in order)."""
    return next((r for r in reversed(rows) if r.enabled), None)


def renumber(rows: list[Outbound]) -> None:
    for i, row in enumerate(rows, start=1):
        row.position = i


def check_order(rows: list[Outbound]) -> None:
    enabled = [r for r in rows if r.enabled]
    if not any(r.mode != OutboundMode.block for r in enabled):
        raise OutboundOrderError("At least one outbound other than Block must be enabled")
    if enabled[-1].mode == OutboundMode.block:
        raise OutboundOrderError("Block can not be the last (default) outbound: it would block everything")


def _mark_default(rows: list[Outbound]) -> None:
    default = default_row(rows)
    for r in rows:
        r.is_default = r is default


def warp_mode_for(rows: list[Outbound]) -> str | None:
    """The settings' WARP mode matching the outbounds: disable / all (WARP is the default) / custom."""
    warp = next((r for r in rows if r.mode == OutboundMode.warp), None)
    if warp is None:
        return None
    if not warp.enabled:
        return "disable"
    return "all" if warp is default_row(rows) else "custom"


_syncing_setting = False


def _sync_warp_setting(child_id: int, rows: list[Outbound]) -> None:
    """WARP outbound on/off and default follow into the WARP setting (which also runs the WARP service)."""
    global _syncing_setting
    from hiddifypanel.models import ConfigEnum, hconfig, set_hconfig

    wanted = warp_mode_for(rows)
    if wanted is None or str(hconfig(ConfigEnum.warp_mode, child_id) or "") == wanted:
        return
    _syncing_setting = True
    try:
        set_hconfig(ConfigEnum.warp_mode, wanted, child_id, commit=False)
    finally:
        _syncing_setting = False


def finalize(child_id: int, rows: list[Outbound], *, sync_setting: bool = True) -> None:
    """Validate the order, renumber, mark the default and update the WARP setting. Raises OutboundOrderError."""
    rows = sorted(rows, key=lambda r: (r.position or 0, r.id or 0))
    check_order(rows)
    renumber(rows)
    _mark_default(rows)
    if sync_setting:
        _sync_warp_setting(child_id, rows)


def move_before_default(rows: list[Outbound], row: Outbound) -> list[Outbound]:
    """``rows`` in order with ``row`` placed just before the default (last enabled) outbound."""
    others = [r for r in rows if r is not row]
    default = default_row(others)
    at = others.index(default) if default is not None else len(others)
    others.insert(at, row)
    renumber(others)
    return others


def move_to_end(rows: list[Outbound], row: Outbound) -> list[Outbound]:
    out = [r for r in rows if r is not row] + [row]
    renumber(out)
    return out


def _warp_setting_enabled(child_id: int) -> bool:
    try:
        from hiddifypanel.models import ConfigEnum, hconfig

        return str(hconfig(ConfigEnum.warp_mode, child_id) or "disable") != "disable"
    except Exception:
        return False


def _initial_order(rows: list[Outbound]) -> list[Outbound]:
    """Order for rows from before ordering existed: block, exits, WARP, direct; the old default last."""
    rows = sorted(rows, key=lambda r: (RULE_ORDER.index(r.mode) if r.mode in RULE_ORDER else len(RULE_ORDER), r.id or 0))
    legacy_default = next((r for r in rows if r.is_default and r.mode != OutboundMode.block), None)
    if legacy_default is not None:
        rows = [r for r in rows if r is not legacy_default] + [legacy_default]
    return rows


def _repoint_outbound_ids(mapping: dict[int, int]) -> None:
    """Admins' default outbound and users' preferred outbound that pointed at a removed copy now point at the one kept."""
    from hiddifypanel.models import AdminUser
    from hiddifypanel.models.user import User

    for old, new in mapping.items():
        AdminUser.query.filter(AdminUser.default_outbound_id == old).update({"default_outbound_id": new})
    for user in User.query.filter(User.extra_params.isnot(None), User.extra_params != "", User.extra_params != "{}").all():
        extra = user.extra_params_json()
        oid = preferred_outbound_id(extra)
        if oid in mapping:
            extra["preferred_outbound"] = mapping[oid]
            user.extra_params = json.dumps(extra, ensure_ascii=False)


def dedupe_builtin_outbounds(rows: list[Outbound]) -> int:
    """WARP, Direct and Block exist once. Copies (made by restores / syncs that named them differently) are merged
    into the one whose slug is its mode (else the oldest); edited lists are kept. Returns how many copies were removed."""
    removed = 0
    mapping: dict[int, int] = {}
    for mode in BUILTIN_MODES:
        same = [r for r in rows if r.mode == mode]
        if len(same) < 2:
            continue
        same.sort(key=lambda r: (r.slug != str(mode), r.id or 0))
        keep, extras = same[0], same[1:]
        for extra in extras:
            if not keep.lists_override and extra.lists_override:
                _apply_lists(keep, current_lists(extra))
                keep.lists_override = True
            if extra.id is not None and keep.id is not None:
                mapping[extra.id] = keep.id
            rows.remove(extra)
            db.session.delete(extra)
            removed += 1
        keep.is_builtin = True
        keep.slug = str(mode)
    if removed:
        db.session.flush()
        if mapping:
            _repoint_outbound_ids(mapping)
        logger.info(f"Removed {removed} duplicated built-in outbound(s)")
    return removed


def sync_builtin_outbounds(child_id: int = 0, *, commit: bool = True) -> int:
    """Create missing built-in outbounds, refresh the lists the admin has not edited, keep the order valid.

    Returns how many rows were added or changed.
    """
    changed = 0
    rows = Outbound.query.all()
    if rows and _is_child_panel():
        return 0  # the parent decides; only an empty node gets the built-ins until its first sync
    removed = dedupe_builtin_outbounds(rows)
    if removed:
        changed += removed
        renumber(sorted(rows, key=lambda r: (r.position or 0, r.id or 0)))
    for r in rows:
        if not r.slug:
            r.slug = str(r.mode) if r.is_builtin and not any(o.slug == str(r.mode) for o in rows) else Outbound.make_slug(r.name, r.mode)
            changed += 1
    for mode in BUILTIN_MODES:
        spec = _builtin_spec(mode)
        row = next((r for r in rows if r.mode == mode and r.is_builtin), None) or next((r for r in rows if r.mode == mode), None)
        if row is None:
            # WARP starts off unless the WARP setting already uses it.
            enabled = _warp_setting_enabled(child_id) if mode == OutboundMode.warp else True
            row = Outbound(slug=str(mode), mode=mode, name=spec["name"], is_builtin=True, lists_override=False, enabled=enabled)
            _apply_lists(row, spec["lists"])
            row.builtin_lists = spec["lists"]
            db.session.add(row)
            rows.append(row)
            changed += 1
            continue
        touched = False
        if not row.is_builtin:
            row.is_builtin = True
            touched = True
        if (row.builtin_lists or {}) != spec["lists"]:
            row.builtin_lists = spec["lists"]
            touched = True
        if not row.lists_override and current_lists(row) != spec["lists"]:
            _apply_lists(row, spec["lists"])
            touched = True
        changed += int(touched)

    # Stored entries in today's form: rule-set URLs, xray entries with their geosite:/geoip: prefix.
    for r in rows:
        for field in ("rule_sets", "geosites"):
            normal = clean_list(field, getattr(r, field) or [])
            if normal != list(getattr(r, field) or []):
                setattr(r, field, normal)
                changed += 1

    positions = [r.position for r in rows]
    if any(not p for p in positions) or len(set(positions)) != len(positions):
        rows = _initial_order(rows)
        renumber(rows)
        changed += 1
    else:
        rows.sort(key=lambda r: (r.position or 0, r.id or 0))

    # Keep the routing usable: something other than Block enabled, and not last.
    try:
        check_order(rows)
    except OutboundOrderError:
        direct = next((r for r in rows if r.mode == OutboundMode.direct), None)
        if direct is not None:
            direct.enabled = True
            rows = move_to_end(rows, direct)
            changed += 1
    before = [r.is_default for r in rows]
    _mark_default(rows)
    changed += int(before != [r.is_default for r in rows])

    if commit:
        db.session.commit()
    else:
        db.session.flush()
    return changed


def _is_child_panel() -> bool:
    """A node: its outbounds come from the parent panel and are not edited here."""
    try:
        from hiddifypanel.models import ConfigEnum, PanelMode, hconfig

        return hconfig(ConfigEnum.panel_mode) == PanelMode.child
    except Exception:
        return False


def export_rows() -> list[OutboundModel]:
    """The outbounds in order, as the parent hands them to its nodes and backups (slugs, no ids)."""
    return [r.to_model() for r in ordered_rows()]


def import_rows(items: list[OutboundModel]) -> bool:
    """Make this panel's outbounds equal to the parent's, matched by slug. Returns whether anything changed; commits nothing."""
    changed = Outbound.bulk_register(items, commit=False, remove=True)
    if changed:
        rows = ordered_rows()
        _mark_default(rows)
        _sync_warp_setting(0, rows)
    return changed


def reset_builtin_lists(row: Outbound) -> None:
    """Back to the defaults file's lists; upgrades update them again."""
    spec = _builtin_spec(row.mode)
    row.builtin_lists = spec["lists"]
    _apply_lists(row, spec["lists"])
    row.lists_override = False


def migrate_legacy_settings(child_id: int = 0) -> None:
    """One time: carry the old WARP settings (warp_mode, warp_sites, block_iran_sites) over."""
    from hiddifypanel.models import ConfigEnum, hconfig

    sync_builtin_outbounds(child_id, commit=False)
    rows = ordered_rows(child_id)
    by_mode = {r.mode: r for r in rows if r.is_builtin}
    warp, direct, block = by_mode.get(OutboundMode.warp), by_mode.get(OutboundMode.direct), by_mode.get(OutboundMode.block)
    if not (warp and direct and block):
        return

    warp_mode = str(hconfig(ConfigEnum.warp_mode, child_id) or "disable")
    warp.enabled = warp_mode != "disable"
    rows = move_to_end(rows, warp if warp_mode == "all" else direct)

    extra = clean_list("sites", hconfig(ConfigEnum.warp_sites, child_id) or "")
    extra = [s for s in extra if not invalid_entries("sites", [s])]
    if extra:
        warp.sites = list(dict.fromkeys([*(warp.sites or []), *extra]))
        warp.lists_override = True

    if hconfig(ConfigEnum.block_iran_sites, child_id):
        block.domestic = True
        block.lists_override = True
        warp.domestic = False
        warp.lists_override = True
    finalize(child_id, rows, sync_setting=False)
    db.session.commit()


def align_warp_with_setting(child_id: int = 0) -> None:
    """Order the rows and set the WARP outbound from the WARP setting (for panels set up before ordering)."""
    from hiddifypanel.models import ConfigEnum, hconfig

    sync_builtin_outbounds(child_id, commit=False)
    on_warp_mode_changed(child_id, str(hconfig(ConfigEnum.warp_mode, child_id) or "disable"))
    db.session.commit()


def on_warp_mode_changed(child_id: int, value: str) -> None:
    """The WARP setting drives the WARP outbound: disable = off, all = on and default, custom = on, not default."""
    if _syncing_setting:
        return
    rows = ordered_rows(child_id)
    warp = next((r for r in rows if r.mode == OutboundMode.warp), None)
    direct = next((r for r in rows if r.mode == OutboundMode.direct), None)
    if warp is None or direct is None:
        return
    if value == "disable":
        warp.enabled = False
    elif value == "all":
        warp.enabled = True
        rows = move_to_end(rows, warp)
    elif value == "custom":
        warp.enabled = True
        if warp is default_row(rows):
            direct.enabled = True
            rows = move_to_end(rows, direct)
    try:
        finalize(child_id, rows, sync_setting=False)
    except OutboundOrderError:
        direct.enabled = True
        finalize(child_id, move_to_end(rows, direct), sync_setting=False)


def _builtin_rows(child_id: int) -> dict[OutboundMode, Outbound]:
    return {r.mode: r for r in Outbound.query.filter(Outbound.is_builtin.is_(True)).all()}


def on_warp_sites_changed(child_id: int, old: str, new: str) -> None:
    """The settings' "WARP sites" still work: sites added there are added to WARP, removed ones removed."""
    warp = _builtin_rows(child_id).get(OutboundMode.warp)
    if warp is None:
        return
    before, after = set(clean_list("sites", old or "")), clean_list("sites", new or "")
    removed = before - set(after)
    sites = [x for x in (warp.sites or []) if x not in removed]
    sites += [x for x in after if x not in sites and not invalid_entries("sites", [x])]
    if sites != list(warp.sites or []):
        warp.sites = sites
        warp.lists_override = current_lists(warp) != (warp.builtin_lists or {})


def on_block_domestic_changed(child_id: int, block_domestic: bool) -> None:
    """The settings' "block domestic sites" switch moves the region's sites between Block and WARP."""
    rows = _builtin_rows(child_id)
    block, warp = rows.get(OutboundMode.block), rows.get(OutboundMode.warp)
    if not (block and warp):
        return
    block.domestic = block_domestic
    warp.domestic = False if block_domestic else bool((warp.builtin_lists or {}).get("domestic", True))
    for row in (block, warp):
        row.lists_override = current_lists(row) != (row.builtin_lists or {})


def _config_changed(conf=None, old_value=None, **_kw) -> None:
    from hiddifypanel.models import ConfigEnum

    if conf is None or str(conf.value) == str(old_value) or _is_child_panel():
        return
    if conf.key not in (ConfigEnum.warp_mode, ConfigEnum.warp_sites, ConfigEnum.block_iran_sites):
        return
    try:
        # A savepoint: if this fails (e.g. old migrations, before the outbound table exists),
        # only these changes are undone, not the setting being saved.
        with db.session.begin_nested():
            if conf.key == ConfigEnum.warp_mode:
                on_warp_mode_changed(conf.child_id, str(conf.value))
            elif conf.key == ConfigEnum.warp_sites:
                on_warp_sites_changed(conf.child_id, str(old_value or ""), str(conf.value or ""))
            else:
                on_block_domestic_changed(conf.child_id, str(conf.value).lower() in ("true", "1"))
    except Exception as e:  # never break saving a setting
        logger.warning(f"Outbounds not synced with setting {conf.key}: {e}")


_subscribed = False


def subscribe_events() -> None:
    global _subscribed
    if _subscribed:
        return
    from hiddifypanel import Events

    Events.config_changed.subscribe(_config_changed)
    _subscribed = True


# --------------------------------------------------------------------------- template context


class RuleSetVar(BaseModel):
    tag: str
    url: str
    #: sing-box rule-set format: ``binary`` (.srs) or ``source`` (.json).
    format: str = "binary"


class OutboundVar(BaseModel):
    """One outbound as the server templates see it."""

    id: int
    name: str
    mode: str
    is_default: bool
    #: xray entries with prefix: ``geosite:…`` (domain rule) and ``geoip:…`` (ip rule).
    #: Tag in the xray / hiddify-core configs (`WARP`, `freedom`, `blackhole`/`block`, `socks-3`, …).
    xray_tag: str
    singbox_tag: str
    #: Whether templates must declare an outbound for it (SOCKS-based ones; the others are static).
    custom: bool
    #: Tor / Psiphon: run by hiddify-core itself, which also opens a local SOCKS inbound (host / port) for xray.
    native: bool = False
    #: Which core runs it: ``singbox`` (Tor / Psiphon / hiddify-core JSON) or ``xray`` (xray JSON); the other core uses a SOCKS bridge to host:port.
    runs_in: str = ""
    #: The admin's own entries (custom JSON modes), as parsed JSON objects.
    raw: list[dict[str, Any]] = Field(default_factory=list)
    host: str = ""
    port: int = 0
    username: str = ""
    password: str = ""
    sites: list[str] = Field(default_factory=list)
    geosites: list[str] = Field(default_factory=list)
    geoips: list[str] = Field(default_factory=list)
    rule_sets: list[RuleSetVar] = Field(default_factory=list)

    @property
    def has_xray_rules(self) -> bool:
        return bool(self.sites or self.geosites or self.geoips)

    @property
    def has_singbox_rules(self) -> bool:
        return bool(self.sites or self.rule_sets)


class UserRouteVar(BaseModel):
    """Users whose traffic all leaves through one outbound (their preferred outbound)."""

    xray_tag: str
    singbox_tag: str
    #: Block: rejected in hiddify-core (no outbound), blackhole in xray.
    block: bool = False
    uuids: list[str] = Field(default_factory=list)


class OutboundsVar(BaseModel):
    """All outbounds in rule order, plus the final (default) tags."""

    items: list[OutboundVar] = Field(default_factory=list)
    #: Per-user preferred outbounds; these rules come before the site rules.
    user_routes: list[UserRouteVar] = Field(default_factory=list)
    region: str = ""
    default_xray_tag: str = "freedom"
    default_singbox_tag: str = "freedom"

    @property
    def custom(self) -> list[OutboundVar]:
        return [o for o in self.items if o.custom]

    @property
    def xray_socks(self) -> list[OutboundVar]:
        """SOCKS outbounds xray declares: the admin's SOCKS servers and everything hiddify-core runs (reached on its local SOCKS inbounds)."""
        return [o for o in self.items if o.custom and o.runs_in != "xray"]

    @property
    def custom_socks(self) -> list[OutboundVar]:
        """SOCKS outbounds hiddify-core declares: the admin's SOCKS servers and the entries xray runs (reached on xray's local SOCKS inbounds)."""
        return [o for o in self.items if o.custom and not o.native and o.runs_in != "singbox"]

    @property
    def singbox_bridged(self) -> list[OutboundVar]:
        """Run by hiddify-core, reached by xray: each gets a local SOCKS inbound that routes into it."""
        return [o for o in self.items if o.runs_in == "singbox"]

    @property
    def xray_bridged(self) -> list[OutboundVar]:
        """Run by xray, reached by hiddify-core: each gets a local SOCKS inbound that routes into it."""
        return [o for o in self.items if o.runs_in == "xray"]

    def raw_of(self, mode: str) -> list[dict[str, Any]]:
        """The admin's entries of one custom mode, in outbound order."""
        return [entry for o in self.items if o.mode == mode for entry in o.raw]

    @property
    def singbox_raw_outbounds(self) -> list[dict[str, Any]]:
        return self.raw_of("core_outbound")

    @property
    def singbox_raw_endpoints(self) -> list[dict[str, Any]]:
        return self.raw_of("core_endpoint")

    @property
    def xray_raw_outbounds(self) -> list[dict[str, Any]]:
        return self.raw_of("xray_outbound")

    @property
    def native(self) -> list[OutboundVar]:
        """Tor / Psiphon outbounds hiddify-core runs; only the enabled ones are here."""
        return [o for o in self.items if o.native]

    @property
    def rule_sets(self) -> list[RuleSetVar]:
        """Every rule-set any outbound uses, once."""
        seen: dict[str, RuleSetVar] = {}
        for o in self.items:
            for rs in o.rule_sets:
                seen.setdefault(rs.tag, rs)
        return list(seen.values())


def rule_set_var(item: str) -> RuleSetVar:
    """Tag (file name + a short hash, unique per URL) and format of a rule-set URL."""
    url = rule_set_url(item)  # rows saved before rule-sets were URLs may still hold names
    file_name = url.split("?", 1)[0].rsplit("/", 1)[-1].lower()
    fmt = "source" if file_name.endswith(".json") else "binary"
    stem = re.sub(r"[^a-z0-9-]+", "-", file_name.rsplit(".", 1)[0]).strip("-") or "rule-set"
    return RuleSetVar(tag=f"{stem}-{hashlib.sha1(url.encode()).hexdigest()[:6]}", url=url, format=fmt)


def _tags(row: Outbound, warp_available: bool) -> tuple[str, str]:
    if row.mode in CUSTOM_CONFIG_MODES:
        custom_config.parse(row.mode, row.config)  # raises when what is stored is not valid
        tag = custom_config.custom_tag(row)  # the slug: the panel gives the object its tag
        return tag, tag
    match row.mode:
        case OutboundMode.warp:
            return ("WARP", "WARP") if warp_available else ("freedom", "freedom")
        case OutboundMode.direct:
            return "freedom", "freedom"
        case OutboundMode.block:
            return "blackhole", "block"
        case OutboundMode.socks:
            return f"socks-{row.id}", f"socks-{row.id}"
        case _:
            return str(row.mode), str(row.mode)


NATIVE_MODES = (OutboundMode.tor, OutboundMode.psiphon)


def tor_available() -> bool:
    """hiddify-core starts the ``tor`` program itself; without it the whole core would refuse to start."""
    import shutil

    return shutil.which("tor") is not None


def preferred_outbound_id(extra: dict[str, Any]) -> int | None:
    """The user's preferred outbound id from extra params (``preferred_outbound``), or None."""
    value = extra.get("preferred_outbound")
    try:
        return int(value) if value not in (None, "", False) else None
    except (TypeError, ValueError):
        return None


def admin_default_outbounds() -> dict[int, int]:
    """Admin id → the outbound id its users leave through by default.

    An admin's own choice wins; else its nearest parent's; admins with none are left out (automatic).
    """
    from hiddifypanel.models import AdminUser

    admins = {a.id: a for a in AdminUser.query.all()}
    resolved: dict[int, int] = {}
    for admin in admins.values():
        seen: set[int] = set()
        cur = admin
        while cur is not None and cur.id not in seen:
            seen.add(cur.id)
            if cur.default_outbound_id:
                resolved[admin.id] = int(cur.default_outbound_id)
                break
            cur = admins.get(cur.parent_admin_id) if cur.parent_admin_id and cur.parent_admin_id != cur.id else None
    return resolved


def _user_routes(rows: list[Outbound], items: list[OutboundVar]) -> list[UserRouteVar]:
    from hiddifypanel.models.user import User

    by_id = {o.id: o for o in items}
    legacy_by_mode = {o.mode: o for o in items}
    admin_default = admin_default_outbounds()
    uuids: dict[int, list[str]] = {}
    for user in User.query.filter(User.deleted.is_(False)).all():
        extra = user.extra_params_json() if user.extra_params and user.extra_params.strip() not in ("", "{}") else {}
        oid = preferred_outbound_id(extra)
        target = by_id.get(oid) if oid is not None else None
        # Older panels: extra {"outbound": "warp"} meant "this user goes through WARP".
        if target is None and isinstance(extra.get("outbound"), str):
            target = legacy_by_mode.get(extra["outbound"].strip().lower())
        # The user chose nothing: the owner's (or the nearest admin above's) default.
        if target is None:
            target = by_id.get(admin_default.get(user.added_by or 0, 0))
        if target is not None:
            uuids.setdefault(target.id, []).append(user.uuid)
    return [
        UserRouteVar(
            xray_tag=o.xray_tag,
            singbox_tag=o.singbox_tag,
            block=o.mode == OutboundMode.block,
            uuids=sorted(uuids[o.id]),
        )
        for o in items
        if o.id in uuids
    ]


def build_outbounds_var(child_id: int = 0, hconfig: Any = None) -> OutboundsVar:
    """The routing data for the server templates of ``child_id``."""
    from hiddifypanel.models import ConfigEnum
    from hiddifypanel.models import hconfig as get_hconfig

    def conf(key: ConfigEnum) -> Any:
        if hconfig is not None:
            return getattr(hconfig, str(key), None)
        return get_hconfig(key, child_id)

    region = REGION_BY_COUNTRY.get(str(conf(ConfigEnum.country) or ""), "cn")
    domestic = (load_defaults().get("domestic") or {}).get(region) or {}
    warp_available = str(conf(ConfigEnum.warp_mode) or "disable") != "disable"

    # In the admin's order; the last enabled one is the default (route final).
    rows = [r for r in ordered_rows(child_id) if r.enabled]
    if not tor_available() and any(r.mode == OutboundMode.tor for r in rows):
        logger.warning("The Tor outbound is on but the `tor` program is not installed: it is left out of the configs")
        rows = [r for r in rows if r.mode != OutboundMode.tor]
    default = rows[-1] if rows and rows[-1].mode != OutboundMode.block else None

    items: list[OutboundVar] = []
    for row in rows:
        try:
            xray_tag, singbox_tag = _tags(row, warp_available)
        except custom_config.CustomOutboundError as e:  # stored before the checks, or edited in the database: leave it out
            logger.warning(f"The custom outbound '{row.name}' is not valid and is left out of the configs: {e}")
            if row is default:
                default = None
            continue
        sites = list(row.sites or [])
        geosites = list(row.geosites or [])
        rule_sets = list(row.rule_sets or [])
        if row.domestic:
            sites += clean_list("sites", domestic.get("sites") or [])
            geosites += clean_list("geosites", domestic.get("geosites") or [])
            rule_sets += clean_list("rule_sets", domestic.get("rule_sets") or [])
        endpoint = default_endpoint(row.mode)
        configurable = row.mode in CONFIGURABLE_ENDPOINT_MODES
        is_custom_json = row.mode in CUSTOM_CONFIG_MODES
        if is_custom_json:
            endpoint = {"host": "127.0.0.1", "port": custom_config.bridge_port(row.id)}
            raw = [custom_config.parse(row.mode, row.config).with_tag(singbox_tag)]
            runs_in = "xray" if row.mode == OutboundMode.xray_outbound else "singbox"
        else:
            raw = []
            runs_in = "singbox" if row.mode in NATIVE_MODES else ""
        if row is default:
            # Everything else goes to the default anyway: its own lists add nothing.
            sites, geosites, rule_sets = [], [], []
        # xray: geosite:… entries go in the domain rule, geoip:… in the ip rule.
        geoips = [g for g in dict.fromkeys(geosites) if g.startswith("geoip:")]
        geosites = [g for g in dict.fromkeys(geosites) if not g.startswith("geoip:")]
        items.append(
            OutboundVar(
                id=row.id,
                name=row.name,
                mode=str(row.mode),
                is_default=row is default,
                xray_tag=xray_tag,
                singbox_tag=singbox_tag,
                custom=row.mode in ENDPOINT_MODES,
                native=row.mode in NATIVE_MODES,
                runs_in=runs_in,
                raw=raw,
                # Tor / Psiphon: always their local port from the defaults file.
                host=(row.host if configurable and row.host else str(endpoint.get("host") or "")),
                port=int((row.port if configurable and row.port else endpoint.get("port")) or 0),
                username=(row.username or "") if configurable else "",
                password=(row.password or "") if configurable else "",
                sites=list(dict.fromkeys(sites)),
                geosites=geosites,
                geoips=geoips,
                rule_sets=[rule_set_var(x) for x in dict.fromkeys(rule_sets)],
            )
        )

    out = OutboundsVar(items=items, region=region, user_routes=_user_routes(rows, items))
    final = next((o for o in items if o.is_default), None)
    if final is not None:
        out.default_xray_tag, out.default_singbox_tag = final.xray_tag, final.singbox_tag
    return out


__all__ = [
    "BUILTIN_MODES",
    "MULTI_MODES",
    "OutboundVar",
    "OutboundsVar",
    "build_outbounds_var",
    "clean_list",
    "invalid_entries",
    "load_defaults",
    "migrate_legacy_settings",
    "reset_builtin_lists",
    "finalize",
    "move_before_default",
    "move_to_end",
    "subscribe_events",
    "sync_builtin_outbounds",
]
