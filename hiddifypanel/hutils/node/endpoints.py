"""Which address of a panel (a node, or the parent) to call: a direct domain first, a relay domain if no direct one answers,
a CDN domain if no relay one does.

A panel has several domains. The parent knows the domains of each of its nodes (they come with the registration and every sync); a
node learns the parent's domains from the parent (``parent_hosts`` in what the parent answers). ``NodeApiClient`` asks ``alternates`` for
the addresses to try and moves on to the next one when an address cannot be connected to (and does not try a dead one again for a minute).
"""

from __future__ import annotations

import json
import threading
import time
from collections.abc import Iterable
from dataclasses import dataclass
from urllib.parse import urlparse

from flask import has_app_context
from loguru import logger

from hiddifypanel.cache import redis_client
from hiddifypanel.models.child import Child
from hiddifypanel.models.config import hconfig
from hiddifypanel.models.config_enum import ConfigEnum
from hiddifypanel.models.domain import Domain, DomainType, FakeMode

#: The order of the domains to try: direct, relay, cdn, and the sub link only domains last. A worker domain does not serve the panel's API.
RANK: dict[DomainType, int] = {DomainType.direct: 0, DomainType.relay: 1, DomainType.cdn: 2, DomainType.sub_link_only: 3}
MODE_NAME: dict[DomainType, str] = {DomainType.direct: "direct", DomainType.relay: "relay", DomainType.cdn: "cdn", DomainType.sub_link_only: "sub_link_only"}
_RANK_BY_NAME: dict[str, int] = {MODE_NAME[m]: r for m, r in RANK.items()}

#: An address that could not be connected to is not tried first for this long.
DOWN_SECONDS = 60.0
PARENT_HOSTS_KEY = "node:parent-hosts"
NODE_HOSTS_KEY = "node:hosts"


@dataclass(frozen=True)
class PanelHost:
    domain: str
    mode: str  # "direct" | "relay" | "cdn" | "sub_link_only"


def usable_hosts(domains: Iterable[Domain]) -> list[PanelHost]:
    """The domains the panel's API can be reached on, best first (direct, relay, cdn, sub link only; inside each the admin's own order).
    Only a domain with a valid certificate (not self-signed, not expired, not missing) is one: the other side checks it."""
    rows = [d for d in domains if d.mode in RANK and d.fake_mode == FakeMode.valid and d.tls_status == "valid" and d.domain and "*" not in d.domain]
    rows.sort(key=lambda d: (RANK[d.mode], *Domain.panel_order_key(d)))
    seen: set[str] = set()
    hosts: list[PanelHost] = []
    for d in rows:
        name = d.domain.strip().lower()
        if name not in seen:
            seen.add(name)
            hosts.append(PanelHost(name, MODE_NAME[d.mode]))
    return hosts


def own_hosts(child_id: int | None = None) -> list[PanelHost]:
    """This panel's domains that the other side can call, best first."""
    cid = Child.current().id if child_id is None else child_id
    return usable_hosts(Domain.query.filter(Domain.child_id == cid).all())


def best_own_host() -> str | None:
    hosts = own_hosts()
    return hosts[0].domain if hosts else None


def base_url(host: str, admin_path: str) -> str:
    return f"https://{host}/{admin_path.strip('/')}/"


def ordered_bases(primary: str, hosts: list[PanelHost], admin_path: str) -> list[str]:
    """``primary`` and the addresses of ``hosts``, best first. A primary on a host that is in ``hosts`` takes that host's place in the
    order; a primary that is not (an IP, an old address) is tried first: it is the one that worked when the panel was added."""
    primary = primary.rstrip("/") + "/"
    primary_host = urlparse(primary).netloc.lower()
    ranked = {h.domain: h for h in hosts}
    bases: list[str] = []
    if primary_host not in ranked:
        bases.append(primary)
    for h in hosts:
        url = primary if h.domain == primary_host else base_url(h.domain, admin_path)
        if url not in bases:
            bases.append(url)
    return bases or [primary]


# --------------------------------------------------------------------------- what the parent tells its nodes, and a node its parent


def remember_parent_hosts(hosts: Iterable[PanelHost]) -> None:
    """A node keeps the parent's domains, to move on to another one when the one it uses is down."""
    try:
        redis_client.set(PARENT_HOSTS_KEY, json.dumps([{"domain": h.domain, "mode": h.mode} for h in hosts]))
    except Exception:  # noqa: BLE001  the list is a help, never a reason to fail
        logger.warning("could not keep the parent's domains")


def _read_hosts(key: str) -> list[PanelHost]:
    try:
        raw = redis_client.get(key)
        rows = json.loads(raw) if raw else []
    except Exception:  # noqa: BLE001
        return []
    hosts = [PanelHost(str(r["domain"]), str(r["mode"])) for r in rows if isinstance(r, dict) and r.get("mode") in _RANK_BY_NAME and r.get("domain")]
    return sorted(hosts, key=lambda h: _RANK_BY_NAME[h.mode])


def parent_hosts() -> list[PanelHost]:
    return _read_hosts(PARENT_HOSTS_KEY)


def remember_node_hosts(node_unique_id: str, hosts: Iterable[PanelHost]) -> None:
    """The parent keeps the domains a node says it can be called on (the node knows which of its certificates are valid)."""
    try:
        redis_client.set(f"{NODE_HOSTS_KEY}:{node_unique_id}", json.dumps([{"domain": h.domain, "mode": h.mode} for h in hosts]))
    except Exception:  # noqa: BLE001
        logger.warning("could not keep the domains of a node")


def node_hosts(node_unique_id: str) -> list[PanelHost]:
    return _read_hosts(f"{NODE_HOSTS_KEY}:{node_unique_id}")


# --------------------------------------------------------------------------- the addresses to call


def alternates(base: str) -> list[str]:
    """Every address of the panel at ``base`` to try, best first. Just ``base`` when it is not a panel this one knows more about."""
    primary = base.rstrip("/") + "/"
    if not has_app_context():
        return [primary]
    try:
        host = urlparse(primary).netloc.lower()
        child = _node_at(host)
        if child is not None:  # we are the parent: the domains the node said it can be called on
            hosts = node_hosts(child.unique_id)
            path = hconfig(ConfigEnum.proxy_path_admin, child.id) or urlparse(primary).path
            return ordered_bases(primary, hosts, path)
        parent = (hconfig(ConfigEnum.parent_panel) or "").strip()
        if parent and urlparse(parent.rstrip("/") + "/").netloc.lower() == host:  # we are a node: the parent's domains
            return ordered_bases(primary, parent_hosts(), urlparse(primary).path)
    except Exception:  # noqa: BLE001  without the extra addresses it still works with the one it was given
        logger.exception("could not list the other addresses of a panel")
    return [primary]


def _node_at(host: str) -> Child | None:
    """The node (of this parent) that has ``host`` as its address or as one of its domains."""
    by_url = Child.query.filter(Child.node_base_url.like(f"https://{host}/%") | (Child.node_base_url == f"https://{host}")).first()
    if by_url is not None:
        return by_url
    domain = Domain.query.filter(Domain.domain == host, Domain.child_id != 0).first()
    return Child.by_id(domain.child_id) if domain is not None else None


# --------------------------------------------------------------------------- what is down


_down_until: dict[str, float] = {}
_lock = threading.Lock()


def mark_down(base: str) -> None:
    with _lock:
        _down_until[base] = time.monotonic() + DOWN_SECONDS


def mark_up(base: str) -> None:
    with _lock:
        _down_until.pop(base, None)


def live_first(bases: list[str]) -> list[str]:
    """``bases`` in their order, with the ones that failed in the last minute after the others."""
    now = time.monotonic()
    with _lock:
        down = {b for b in bases if _down_until.get(b, 0.0) > now}
    return [b for b in bases if b not in down] + [b for b in bases if b in down]
