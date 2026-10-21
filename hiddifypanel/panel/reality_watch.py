"""REALITY SNI watch: which REALITY SNIs are filtered on which ISP, and switching a filtered one to a spare.

The panel's server is abroad and can not see filtering in Iran. The full clean IP test (a command run on a device in
Iran, ``clean_ip_script``) also opens a TLS connection to this server with each REALITY SNI and each spare SNI, the way
a REALITY client does: SNI filtering cuts it, whatever the address. Its report lands here, filed under the ISP it came
from. A REALITY SNI that is filtered can be switched to a spare that worked on that ISP and that suits REALITY
(TLS 1.3 + h2): by the admin on the Clean IP page, or by itself when ``reality_sni_auto`` is on.
"""

from __future__ import annotations

import json
import re
import time

from loguru import logger

from hiddifypanel.cache import redis_client
from hiddifypanel.models import ConfigEnum, Domain, FakeMode, hconfig, set_hconfig

_STATUS = "hiddify:reality-sni:status"  # {sni: {isp: {"ok": bool, "at": unix}}}
_EVENTS = "hiddify:reality-sni:events"  # [{at, isp, old, new, auto}], newest last
_NAME = re.compile(r"^(?=.{1,253}$)([a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}$")


class WatchError(Exception):
    """A switch was refused; str(e) is shown to the admin."""


def _json(key: str, default):
    raw = redis_client.get(key)
    return json.loads(raw) if raw else default


def reality_domains() -> list[Domain]:
    return Domain.query.filter(Domain.fake_mode == FakeMode.reality, Domain.child_id == 0).order_by(Domain.id).all()


def spares() -> list[str]:
    names = re.split(r"[\s,;]+", str(hconfig(ConfigEnum.reality_sni_spares) or "").strip().lower())
    return [n for n in dict.fromkeys(names) if _NAME.match(n)]


def settings() -> dict:
    return {"spares": spares(), "auto": bool(hconfig(ConfigEnum.reality_sni_auto))}


def save_settings(spare_names: list[str], auto: bool) -> dict:
    names = [n.strip().lower() for n in spare_names if _NAME.match(n.strip().lower())]
    set_hconfig(ConfigEnum.reality_sni_spares, "\n".join(dict.fromkeys(names)))
    set_hconfig(ConfigEnum.reality_sni_auto, bool(auto))
    return settings()


def targets() -> list[str]:
    """What the full test checks: every REALITY SNI in use, then the spares."""
    names = [d.domain.lower() for d in reality_domains() if d.domain]
    return list(dict.fromkeys(names + spares()))


def status() -> dict:
    return _json(_STATUS, {})


def events() -> list:
    return _json(_EVENTS, [])


def record(isp: str, results: list[dict]) -> list[dict]:
    """Files a report's SNI results under its ISP, then switches what is filtered when the switch is automatic.
    Returns the switches made."""
    now = int(time.time())
    data = status()
    for r in results:
        sni = str(r.get("sni") or "").lower()
        if sni:
            data.setdefault(sni, {})[isp] = {"ok": bool(r.get("ok")), "at": now}
    redis_client.set(_STATUS, json.dumps(data))
    if not hconfig(ConfigEnum.reality_sni_auto):
        return []
    made = []
    for d in reality_domains():
        if data.get(d.domain.lower(), {}).get(isp, {}).get("ok") is False:
            new = _best_spare(isp, data)
            if new is None:
                logger.warning("REALITY SNI {} is filtered on {} and no spare works there", d.domain, isp)
                continue
            try:
                made.append(switch(d, new, isp=isp, auto=True))
            except WatchError as e:
                logger.warning("REALITY SNI {}: no switch to {} ({})", d.domain, new, e)
    return made


def _best_spare(isp: str, data: dict) -> str | None:
    """A spare that worked on this ISP and is not filtered on any ISP it was tested on."""
    used = {d.domain.lower() for d in Domain.query.all() if d.domain}
    for name in spares():
        seen = data.get(name, {})
        if name not in used and seen.get(isp, {}).get("ok") and all(v.get("ok") for v in seen.values()):
            return name
    return None


def switch(domain: Domain, new: str, *, isp: str = "", auto: bool = False) -> dict:
    """The REALITY domain now uses ``new`` as its SNI (name, server names, alias), and the cores get it."""
    from hiddifypanel import hutils
    from hiddifypanel.panel.commercial.restapi.v2.admin.domains_page_api import _save

    new = new.strip().lower()
    if not _NAME.match(new):
        raise WatchError("Not a domain name")
    if Domain.query.filter(Domain.domain == new).first() is not None:
        raise WatchError("This name is already a domain of the panel")
    if domain.fake_mode != FakeMode.reality:
        raise WatchError("Not a REALITY domain")
    # REALITY borrows the site's TLS: it must speak TLS 1.3 and h2 (checked from the server)
    if not hutils.network.is_domain_reality_friendly(new):
        raise WatchError("This site does not suit REALITY (it needs TLS 1.3 and HTTP/2)")
    old = domain.domain
    domain.domain = new
    domain.servernames = new
    if (domain.alias or "") in ("", old):
        domain.alias = new
    _save(domain, is_created=False)
    # A new name: rpxy-l4 (which routes port 443 by SNI) and haproxy need it too, not only the cores _save reloads
    from hiddifypanel.panel.run_commander import Command, commander

    commander(Command.apply)
    event = {"at": int(time.time()), "isp": isp, "old": old, "new": new, "auto": auto}
    redis_client.set(_EVENTS, json.dumps((events() + [event])[-30:]))
    logger.info("REALITY SNI {} switched to {} ({})", old, new, "auto" if auto else "admin")
    return event
