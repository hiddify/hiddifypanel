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
        if name not in used and seen.get(isp, {}).get("ok") and all(v.get("ok") for v in seen.values()) and reality_works(name):
            return name
    return None


def _free_port() -> int:
    import socket

    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def reality_works(sni: str, timeout: int = 10) -> bool:
    """A real REALITY connection with this site as the target, through a throwaway xray server and client on this
    machine. TLS 1.3 + h2 is not enough: some such sites (e.g. one answering with a HelloRetryRequest) close REALITY's
    handshake, and every client would fail after the switch."""
    import subprocess
    import tempfile
    import uuid

    from hiddifypanel.proxy_v3.outbound_custom import XRAY_BIN

    if not XRAY_BIN.exists():
        return False
    keys = subprocess.run([str(XRAY_BIN), "x25519"], capture_output=True, text=True, timeout=10).stdout.splitlines()
    pick = lambda *names: next((line.split(":", 1)[1].strip() for line in keys if line.lower().startswith(names)), "")  # noqa: E731
    private, public = pick("private"), pick("public", "password")
    if not private or not public:
        return False
    user, short = str(uuid.uuid4()), "ab"
    server_port, socks_port = _free_port(), _free_port()
    server = {
        "log": {"loglevel": "none"},
        "inbounds": [{"listen": "127.0.0.1", "port": server_port, "protocol": "vless",
                      "settings": {"clients": [{"id": user, "flow": "xtls-rprx-vision"}], "decryption": "none"},
                      "streamSettings": {"network": "tcp", "security": "reality",
                                         "realitySettings": {"target": f"{sni}:443", "serverNames": [sni], "privateKey": private, "shortIds": [short]}}}],
        "outbounds": [{"protocol": "freedom"}],
    }
    client = {
        "log": {"loglevel": "none"},
        "inbounds": [{"listen": "127.0.0.1", "port": socks_port, "protocol": "socks"}],
        "outbounds": [{"protocol": "vless",
                       "settings": {"vnext": [{"address": "127.0.0.1", "port": server_port, "users": [{"id": user, "flow": "xtls-rprx-vision", "encryption": "none"}]}]},
                       "streamSettings": {"network": "tcp", "security": "reality",
                                          "realitySettings": {"serverName": sni, "fingerprint": "chrome", "publicKey": public, "shortId": short}}}],
    }
    procs = []
    with tempfile.TemporaryDirectory(prefix="reality-") as tmp:
        try:
            for name, cfg in (("server", server), ("client", client)):
                path = f"{tmp}/{name}.json"
                with open(path, "w") as f:
                    json.dump(cfg, f)
                procs.append(subprocess.Popen([str(XRAY_BIN), "run", "-c", path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL))
            time.sleep(1.5)
            out = subprocess.run(
                ["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}", "--max-time", str(timeout), "-x", f"socks5h://127.0.0.1:{socks_port}", "https://cp.cloudflare.com/generate_204"],
                capture_output=True, text=True, timeout=timeout + 5,
            ).stdout
            return out.strip() == "204"
        except Exception:
            return False
        finally:
            for p in procs:
                p.terminate()
                try:
                    p.wait(5)
                except Exception:
                    p.kill()


def switch(domain: Domain, new: str, *, isp: str = "", auto: bool = False) -> dict:
    """The REALITY domain now uses ``new`` as its SNI (name, server names, alias), and the cores get it."""
    from hiddifypanel.panel.commercial.restapi.v2.admin.domains_page_api import _save

    new = new.strip().lower()
    if not _NAME.match(new):
        raise WatchError("Not a domain name")
    if Domain.query.filter(Domain.domain == new).first() is not None:
        raise WatchError("This name is already a domain of the panel")
    if domain.fake_mode != FakeMode.reality:
        raise WatchError("Not a REALITY domain")
    # REALITY borrows the site's TLS: a real REALITY connection to it must work (TLS 1.3 + h2 is not enough)
    if not reality_works(new):
        raise WatchError("REALITY does not work with this site (a test connection through it failed)")
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
