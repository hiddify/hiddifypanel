"""Config tester → the panel's own configs (custom proxies): which ones a test found down, turning them off, and turning
them back on later.

A config in a subscription is named after its custom proxy, then its domain, IP version… (client/tag.j2), so a tested
name belongs to the proxy whose name it starts with (the longest one). A proxy is *down* only when every one of its
tested configs failed: when some domains still work it is *partly down* and stays on.

What the tester turned off is kept (``ConfigEnum.config_tester_disabled``: ``[[proxy id, unix time], …]``) until the
admin turns it back on with Restore: nothing comes back by itself.
"""

from __future__ import annotations

import json
import time
from collections.abc import Iterable
from typing import Literal, TypedDict

from hiddifypanel.database import db
from hiddifypanel.models import Child, ConfigEnum, hconfig, set_hconfig
from hiddifypanel.models.custom_proxy import CustomProxy

type Status = Literal["down", "partial", "up"]


class TestedConfig(TypedDict):
    name: str
    ok: bool


class ProxyHealth(TypedDict):
    id: int
    name: str
    enabled: bool
    status: Status
    tested: int
    failed: int
    #: the failed configs' names (a few), to show what was found
    failed_names: list[str]


class DisabledProxy(TypedDict):
    id: int
    name: str
    #: when the tester turned it off (unix seconds)
    at: int
    #: still off (the admin may have turned it on by hand since)
    off: bool


def _proxies(child_id: int) -> list[CustomProxy]:
    return CustomProxy.query.filter(CustomProxy.child_id == child_id).all()


def owner(name: str, proxies: Iterable[CustomProxy]) -> CustomProxy | None:
    """The proxy a tested config belongs to: the longest proxy name the config's name is, or starts with (then a space)."""
    name = " ".join(name.split())
    best: CustomProxy | None = None
    for proxy in proxies:
        pname = " ".join((proxy.name or "").split())
        if pname and (name == pname or name.startswith(pname + " ")) and (best is None or len(pname) > len(" ".join(best.name.split()))):
            best = proxy
    return best


def health(results: Iterable[TestedConfig], child_id: int | None = None) -> list[ProxyHealth]:
    """Each proxy with tested configs, worst first: down (all failed), partly down, up."""
    child_id = Child.current().id if child_id is None else child_id
    proxies = _proxies(child_id)
    found: dict[int, ProxyHealth] = {}
    for result in results:
        proxy = owner(result["name"], proxies)
        if proxy is None:
            continue
        h = found.setdefault(proxy.id, ProxyHealth(id=proxy.id, name=proxy.name, enabled=bool(proxy.enable), status="up", tested=0, failed=0, failed_names=[]))
        h["tested"] += 1
        if not result["ok"]:
            h["failed"] += 1
            if len(h["failed_names"]) < 5:
                h["failed_names"].append(result["name"])
    for h in found.values():
        h["status"] = "down" if h["failed"] == h["tested"] else "partial" if h["failed"] else "up"
    order = {"down": 0, "partial": 1, "up": 2}
    return sorted(found.values(), key=lambda h: (order[h["status"]], h["name"]))


def _record(child_id: int) -> list[list[int]]:
    try:
        value = json.loads(hconfig(ConfigEnum.config_tester_disabled, child_id) or "[]")
    except ValueError:
        return []
    return [[int(i), int(at)] for i, at in value if isinstance(i, int)] if isinstance(value, list) else []


def _save(child_id: int, record: list[list[int]]) -> None:
    set_hconfig(ConfigEnum.config_tester_disabled, json.dumps(record, separators=(",", ":")), child_id, commit=False)


def disabled(child_id: int | None = None) -> list[DisabledProxy]:
    """What the tester turned off and Restore would turn back on (proxies deleted since are left out)."""
    child_id = Child.current().id if child_id is None else child_id
    by_id = {p.id: p for p in _proxies(child_id)}
    return [DisabledProxy(id=i, name=by_id[i].name, at=at, off=not by_id[i].enable) for i, at in _record(child_id) if i in by_id]


def disable(ids: Iterable[int], child_id: int | None = None) -> list[DisabledProxy]:
    """Turns these proxies off (only enabled ones of this panel) and adds them to what Restore brings back."""
    child_id = Child.current().id if child_id is None else child_id
    wanted = set(ids)
    record = _record(child_id)
    kept = {i for i, _ in record}
    now = int(time.time())
    for proxy in _proxies(child_id):
        if proxy.id not in wanted or not proxy.enable:
            continue
        proxy.enable = False
        if proxy.id not in kept:
            record.append([proxy.id, now])
    _save(child_id, record)
    db.session.commit()
    return disabled(child_id)


def restore(child_id: int | None = None) -> list[DisabledProxy]:
    """Turns back on everything the tester turned off, and forgets it. Answers what was turned on. One that cannot be
    on now (its protocol is off in Settings) stays in the list for a later Restore."""
    child_id = Child.current().id if child_id is None else child_id
    by_id = {p.id: p for p in _proxies(child_id)}
    back: list[DisabledProxy] = []
    waiting: list[list[int]] = []
    for p in disabled(child_id):
        proxy = by_id[p["id"]]
        if not p["off"]:
            continue
        if proxy.blocked_parent_enables():
            waiting.append([p["id"], p["at"]])
            continue
        proxy.enable = True
        back.append(p)
    _save(child_id, waiting)
    db.session.commit()
    return back
