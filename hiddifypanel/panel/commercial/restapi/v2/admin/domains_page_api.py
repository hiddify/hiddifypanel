"""Domains page API (admin v2): list, add (with detection), edit, order, certificates and gateway port checks.

Saving uses the same rules as the classic page (panel/domain_rules.py). Every change needs the server
configs regenerated (``restart_mode: apply_config``).
"""

from __future__ import annotations

import json
import re
import threading
import time
from typing import Any

from apiflask import abort
from flask import request
from flask.views import MethodView
from flask_babel import gettext as _
from loguru import logger
from sqlalchemy.orm import selectinload

from hiddifypanel import g, hutils
from hiddifypanel.auth import login_required
from hiddifypanel.database import db
from hiddifypanel.models import Child, ConfigEnum, CustomProxy, CustomProxyMode, Domain, DomainType, FakeMode, Role, hconfig, set_hconfig
from hiddifypanel.models.domain import normalize_domain_name
from hiddifypanel.models.tls_store import TlsStore
from hiddifypanel.panel import domain_rules
from hiddifypanel.proxy_v3.context_vars.ports import GATEWAY_CLIENT_HTTP_PORT, GATEWAY_CLIENT_TLS_PORT
from hiddifypanel.proxy_v3.domain_proxy_options import REALITY_TERMINATION_SLUG, list_domain_proxy_options, proxy_mode_group
from hiddifypanel.proxy_v3.domain_mode_filter import domain_modes_use_reality

APPLY = "apply_config"
ROLES = {Role.super_admin, Role.admin}
DOMAIN_RE = re.compile(r"^(\*\.)?([A-Za-z0-9\-\.]+\.[a-zA-Z]{2,})$|^(\d{1,3}\.){3}\d{1,3}$|^([0-9a-fA-F]{1,4}:){1,7}(:|[0-9a-fA-F]{1,4})$")
# A domain's own TLS / HTTP port is not served by anything: the firewall redirects it to 443 / 80
# (services/firewall). So no process may listen on it, not even haproxy or rpxy-l4.
#: Settings whose ports belong to other services (a domain gateway port must not take them).
OTHER_SERVICE_PORTS = (
    ConfigEnum.wireguard_port,
    ConfigEnum.reality_port,
    ConfigEnum.special_port,
    ConfigEnum.shadowsocks2022_port,
    ConfigEnum.naive_port,
    ConfigEnum.mieru_tcp_ports,
    ConfigEnum.kcp_ports,
)
#: Ports no gateway may use (system services, the panel's own internal ports).
SYSTEM_PORTS = {22, 53, 3306, 6379, 9000}
CERT_JOB_TTL = 600


def _child_id() -> int:
    return Child.current().id


def _ports(value: Any) -> set[int]:
    out: set[int] = set()
    for part in re.split(r"[\s,;]+", str(value or "")):
        if part.isdigit() and 0 < int(part) < 65536:
            out.add(int(part))
    return out


def _enum(value):
    return value.value if hasattr(value, "value") else value


# ---------------------------------------------------------------------------------------------- rows


def _tls_out(d: Domain) -> dict[str, Any]:
    cert = d.certificate
    return {
        "status": d.tls_status,
        "needs_valid": bool(d.need_valid_ssl),
        "issuer": (cert.issuer if cert else "") or "",
        "expires_at": cert.expires_at.isoformat() + "Z" if cert and cert.expires_at else None,
        "updated_at": cert.updated_at.isoformat() + "Z" if cert and cert.updated_at else None,
        "error": (cert.last_renewal_error if cert else "") or "",
        "job": _cert_job(d),
    }


def _panel_link(d: Domain) -> str | None:
    if d.fake_mode in (FakeMode.fake, FakeMode.reality) or not d.domain or not d.is_accessible():
        return None
    from hiddifypanel.panel import hiddify

    host = d.domain.replace("*", hutils.random.get_random_string(5, 15)) if "*" in d.domain else d.domain
    try:
        return hiddify.get_account_panel_link(g.account, host)
    except Exception:
        return None


def _row_out(d: Domain) -> dict[str, Any]:
    try:
        extra = json.loads(d.extra_params or "{}")
    except ValueError:
        extra = {}
    return {
        "id": d.id,
        "domain": d.domain or "",
        "alias": d.alias or "",
        "mode": _enum(d.mode),
        "fake_mode": _enum(d.fake_mode),
        "sort_order": d.sort_order,
        "custom_proxy_ids": [p.id for p in (d.custom_proxies or []) if p and p.slug != REALITY_TERMINATION_SLUG],
        "show_domain_ids": [x.id for x in (d.show_domains or [])],
        "server_domain_id": d.server_domain_id,
        "download_domain_id": d.download_domain_id,
        "cdn_ip": d.cdn_ip or "",
        "resolve_ip": bool(d.resolve_ip),
        "ech": bool(d.ech),
        "servernames": d.servernames or "",
        "extra_params": json.dumps(extra, indent=2, ensure_ascii=False) if extra else "{}",
        "tls_port": d.tls_port,
        "http_port": d.http_port,
        "tls": _tls_out(d),
        "panel_link": _panel_link(d),
    }


def _domains(child_id: int) -> list[Domain]:
    return (
        Domain.query.filter(Domain.child_id == child_id)
        .options(selectinload(Domain.certificate).defer(TlsStore.private_key), selectinload(Domain.show_domains))
        .order_by((Domain.mode != DomainType.sub_link_only), *Domain.ordering())  # sub-link domains always on top
        .all()
    )


#: Custom proxy modes a domain can pick, and how the page groups them.
_PROXY_KIND = {
    CustomProxyMode.domains_l7_gateway: "l7",
    CustomProxyMode.domains_sni_gateway: "sni",
    CustomProxyMode.ip: "ip",
    CustomProxyMode.domains_auto_public_ports: "ip",
    CustomProxyMode.domains_single_public_port: "ip",
}


def ip_based_allowed(mode, fake_mode) -> bool:
    """IP-based custom proxies are only offered for valid direct domains."""
    return mode == DomainType.direct and fake_mode == FakeMode.valid


def _proxies_list(child_id: int) -> list[dict[str, Any]]:
    """Custom proxies a domain can use."""
    rows = (
        CustomProxy.query.filter(
            CustomProxy.child_id == child_id,
            CustomProxy.slug != REALITY_TERMINATION_SLUG,
            CustomProxy.mode.in_(list(_PROXY_KIND)),
        )
        .order_by(CustomProxy.sort_order, CustomProxy.name)
        .all()
    )
    return [
        {
            "id": p.id,
            "name": p.name,
            "slug": p.slug,
            "kind": _PROXY_KIND[p.mode],
            "group": proxy_mode_group(p.mode),
            "enabled": bool(p.enable),
            "reality": domain_modes_use_reality(p.domain_modes),
        }
        for p in rows
    ]


def _compatible_proxies(child_id: int) -> dict[str, list[int]]:
    """Which custom proxies fit each kind of domain (only the edit dialog needs it)."""
    enabled = CustomProxy.query.filter(CustomProxy.enable == True, CustomProxy.child_id == child_id).all()
    compatible = {}
    for mode in DomainType:
        for fake in FakeMode:
            ids = [o["id"] for o in list_domain_proxy_options(child_id=child_id, mode=mode, fake_mode=fake, proxies=enabled) if ip_based_allowed(mode, fake) or o["group"] != "ip_based"]
            compatible[f"{mode.value}:{fake.value}"] = ids
    return compatible


def _show_options(child_id: int) -> list[dict[str, Any]]:
    """Domains whose configs a domain can show: this panel's and its nodes' (not subscription-only ones)."""
    rows = Domain.query.filter(Domain.mode != DomainType.sub_link_only).order_by(Domain.child_id, Domain.domain).all()
    out = []
    for d in rows:
        node = None if d.child_id == child_id else (d.child.name if d.child else str(d.child_id))
        out.append({"id": d.id, "domain": d.domain or "", "alias": d.alias or "", "mode": _enum(d.mode), "fake_mode": _enum(d.fake_mode), "node": node})
    return out


def _list_out(child_id: int) -> dict[str, Any]:
    domains = _domains(child_id)
    return {
        "domains": [_row_out(d) for d in domains],
        "meta": {
            "ech_enabled": bool(hconfig(ConfigEnum.tls_ech_enable)),
            "cloudflare": bool(hconfig(ConfigEnum.cloudflare)),
            "has_sublink": any(d.mode == DomainType.sub_link_only for d in domains),
            "default_tls_port": GATEWAY_CLIENT_TLS_PORT,
            "default_http_port": GATEWAY_CLIENT_HTTP_PORT,
            "is_super_admin": g.account.role == Role.super_admin,
            "proxies": _proxies_list(child_id),
        },
    }


# ---------------------------------------------------------------------------------------------- ports


def reserved_ports(child_id: int, *, kind: str, domain_id: int | None = None) -> dict[int, str]:
    """Ports a domain's gateway ``kind`` (tls/http) port must not use, with who uses them."""
    used: dict[int, str] = {p: "system" for p in SYSTEM_PORTS}
    for key in OTHER_SERVICE_PORTS:
        for p in _ports(hconfig(key)):
            used.setdefault(p, f"setting:{key.name}")
    # The gateway ports the panel itself serves (settings), for both kinds.
    for p in _ports(hconfig(ConfigEnum.tls_ports)) | {GATEWAY_CLIENT_TLS_PORT}:
        used.setdefault(p, "gateway:tls")
    for p in _ports(hconfig(ConfigEnum.http_ports)) | {GATEWAY_CLIENT_HTTP_PORT}:
        used.setdefault(p, "gateway:http")
    # A TLS port of one domain can not be the HTTP port of another one (same server), and the other way round.
    for d in Domain.query.filter(Domain.child_id == child_id).all():
        if d.id == domain_id:
            continue
        p = d.http_port if kind == "tls" else d.tls_port
        if p:
            used[int(p)] = f"domain:{d.domain}"
    # Custom proxies listening on their own ports.
    for proxy in CustomProxy.query.filter(CustomProxy.child_id == child_id).all():
        if proxy.mode in (CustomProxyMode.domains_l7_gateway, CustomProxyMode.domains_sni_gateway, CustomProxyMode.domains_dns_gateway, CustomProxyMode.no_inbound):
            continue
        if not proxy.enable:
            continue
        for p in [*(proxy.server_inbound_tcp_ports or []), *(proxy.server_inbound_udp_ports or [])]:
            for port in _ports(p):
                used.setdefault(port, f"proxy:{proxy.name}")
    return used


def port_owners(port: int) -> list[str] | None:
    """Processes listening on ``port`` (via root ``lsof``; any of them, haproxy and rpxy-l4 too), or None when it can not be checked."""
    from hiddifypanel.panel.run_commander import Command, commander

    try:
        out = commander(Command.port_owner, run_in_background=False, port=port) or ""
    except Exception as e:
        logger.warning(f"port owner check failed for {port}: {e}")
        return None
    return [line.strip() for line in out.splitlines() if line.strip()]


def port_problem(port: int | None, *, kind: str, child_id: int, domain_id: int | None = None, check_owner: bool = True) -> dict[str, Any] | None:
    """None when ``port`` is fine as this domain's ``kind`` gateway port; otherwise ``{code, detail}``."""
    default = GATEWAY_CLIENT_TLS_PORT if kind == "tls" else GATEWAY_CLIENT_HTTP_PORT
    if port in (None, 0, default):
        return None
    if not isinstance(port, int) or not 1 <= port <= 65535:
        return {"code": "invalid", "detail": ""}
    used = reserved_ports(child_id, kind=kind, domain_id=domain_id)
    if port in used:
        return {"code": "reserved", "detail": used[port]}
    if check_owner:
        owners = port_owners(port)
        if owners is None:
            return {"code": "unknown", "detail": ""}
        if owners:
            return {"code": "busy", "detail": ", ".join(owners)}
    return None


# ---------------------------------------------------------------------------------------------- certificates


def _cert_key(domain_id: int) -> str:
    return f"domains-page:cert:{domain_id}"


def _cert_job(d: Domain) -> dict[str, Any] | None:
    try:
        from hiddifypanel.cache import redis_client

        raw = redis_client.get(_cert_key(d.id))
        return json.loads(raw) if raw else None
    except Exception:
        return None


def _set_cert_job(domain_id: int, job: dict[str, Any]) -> None:
    try:
        from hiddifypanel.cache import redis_client

        redis_client.set(_cert_key(domain_id), json.dumps(job), ex=CERT_JOB_TTL)
    except Exception as e:
        logger.debug(f"cert job state unavailable: {e}")


def start_certificate(d: Domain) -> bool:
    """Ask acme.sh for a real certificate in the background; its state is kept for the page to poll."""
    from hiddifypanel.panel.run_commander import Command, commander

    if not d.need_valid_ssl or not d.domain or "*" in d.domain:
        return False
    domain_id, name = d.id, d.domain
    _set_cert_job(domain_id, {"state": "running", "started": time.time()})

    def run():
        try:
            commander(Command.get_cert, run_in_background=False, domain=name)
            _set_cert_job(domain_id, {"state": "done", "finished": time.time()})
        except Exception as e:
            logger.warning(f"get-cert failed for {name}: {e}")
            _set_cert_job(domain_id, {"state": "failed", "finished": time.time(), "error": str(e)[-500:]})

    threading.Thread(target=run, daemon=True).start()
    return True


# ---------------------------------------------------------------------------------------------- saving


def _get_domain(domain_id: int) -> Domain:
    d = Domain.query.filter(Domain.id == domain_id, Domain.child_id == _child_id()).first()
    if not d:
        abort(404, "Domain not found")
    return d


def _ref(domain_id, child_id: int, *, cross_child: bool = False) -> Domain | None:
    if domain_id in (None, "", 0):
        return None
    q = Domain.query.filter(Domain.id == int(domain_id))
    if not cross_child:
        q = q.filter(Domain.child_id == child_id)
    ref = q.first()
    if not ref:
        abort(400, "Unknown domain reference")
    return ref


def _port_value(body: dict, key: str) -> int | None:
    value = body.get(key)
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        abort(400, f"{key} must be a number")


def _apply_body(d: Domain, body: dict[str, Any], child_id: int) -> None:
    if "domain" in body:
        name = str(body.get("domain") or "").strip().lower()
        if name and not DOMAIN_RE.match(name):
            abort(400, _("Should be a valid domain"))
        d.domain = name
    if "alias" in body:
        d.alias = str(body.get("alias") or "").strip()[:200]
    if "mode" in body:
        try:
            d.mode = DomainType(str(body["mode"]))
        except ValueError:
            abort(400, "Unknown domain mode")
    if "fake_mode" in body:
        try:
            d.fake_mode = FakeMode(str(body["fake_mode"]))
        except ValueError:
            abort(400, "Unknown TLS mode")
    if "custom_proxy_ids" in body:
        ids = [int(i) for i in body.get("custom_proxy_ids") or []]
        rows = CustomProxy.query.filter(CustomProxy.child_id == child_id, CustomProxy.id.in_(ids)).all() if ids else []
        if len(rows) != len(set(ids)):
            abort(400, "Unknown custom proxy")
        by_id = {p.id: p for p in rows}
        d.custom_proxies = [by_id[i] for i in dict.fromkeys(ids)]
    if d.custom_proxies and not ip_based_allowed(d.mode, d.fake_mode):
        # Another mode: IP-based proxies do not apply (only valid direct domains use them).
        d.custom_proxies = [p for p in d.custom_proxies if _PROXY_KIND.get(p.mode) != "ip"]
    if "show_domain_ids" in body:
        ids = [int(i) for i in body.get("show_domain_ids") or []]
        d.show_domains = Domain.query.filter(Domain.id.in_(ids)).all() if ids else []
    if "server_domain_id" in body:
        d.server_domain = _ref(body.get("server_domain_id"), child_id)
    if "download_domain_id" in body:
        d.download_domain = _ref(body.get("download_domain_id"), child_id)
    for key in ("cdn_ip", "servernames"):
        if key in body:
            setattr(d, key, str(body.get(key) or "").strip())
    for key in ("resolve_ip", "ech"):
        if key in body:
            setattr(d, key, bool(body.get(key)))
    if "extra_params" in body:
        raw = body.get("extra_params")
        try:
            parsed = json.loads(raw) if isinstance(raw, str) and raw.strip() else (raw or {})
        except ValueError:
            abort(400, "Extra params must be valid JSON")
        if not isinstance(parsed, dict):
            abort(400, "Extra params must be a JSON object")
        text = json.dumps(parsed, ensure_ascii=False) if parsed else "{}"
        if len(text) > 2000:
            abort(400, "Extra params are too long")
        d.extra_params = text
    for key, kind in (("tls_port", "tls"), ("http_port", "http")):
        if key in body:
            port = _port_value(body, key)
            if problem := port_problem(port, kind=kind, child_id=child_id, domain_id=d.id):
                abort(400, f"{key}: {problem['code']} {problem['detail']}".strip())
            default = GATEWAY_CLIENT_TLS_PORT if kind == "tls" else GATEWAY_CLIENT_HTTP_PORT
            setattr(d, key, None if port in (None, 0, default) else port)


def _save(d: Domain, *, is_created: bool) -> list[str]:
    try:
        warnings = domain_rules.validate_domain(d, is_created=is_created)
    except domain_rules.DomainRuleError as e:
        db.session.rollback()
        abort(400, str(e))
    if not d.alias:
        d.alias = d.domain
    db.session.commit()
    if hconfig(ConfigEnum.first_setup):
        set_hconfig(ConfigEnum.first_setup, False)
    return warnings


class DomainsPageApi(MethodView):
    decorators = [login_required(ROLES)]

    def get(self):
        """Domains page: every domain in order, with TLS status and what the page needs to edit them"""
        from hiddifypanel.panel.fake_proxy_domains import sync_all_configs_to_domains

        sync_all_configs_to_domains(_child_id())  # Telegram / ShadowTLS / SS FakeTLS rows follow their settings
        return _list_out(_child_id())

    def post(self):
        """Add a domain (and ask for its certificate when it needs a real one)"""
        body = request.get_json(silent=True) or {}
        child_id = _child_id()
        existing = _domains(child_id)
        for pos, row in enumerate(existing):  # number the current order, the new domain goes last
            row.sort_order = pos
        d = Domain(child_id=child_id, domain="", alias="", mode=DomainType.direct, fake_mode=FakeMode.valid, cdn_ip="", servernames="", extra_params="{}")
        d.sort_order = len(existing)
        _apply_body(d, body, child_id)
        db.session.add(d)
        warnings = _save(d, is_created=True)
        cert = start_certificate(d)
        return {"created_id": d.id, "certificate_requested": cert, "warnings": warnings, "restart_mode": APPLY, **_list_out(child_id)}


class DomainsPageOptionsApi(MethodView):
    decorators = [login_required(ROLES)]

    def get(self):
        """What only the edit dialog needs, loaded when it opens: which proxies fit each kind of domain, and the domains a sub-link domain can show"""
        child_id = _child_id()
        return {"compatible": _compatible_proxies(child_id), "show_options": _show_options(child_id)}


class DomainsPageItemApi(MethodView):
    decorators = [login_required(ROLES)]

    def patch(self, domain_id: int):
        """Edit a domain; a real certificate is asked for again when the name or mode changed"""
        d = _get_domain(domain_id)
        before = (d.domain, d.mode, d.fake_mode)
        _apply_body(d, request.get_json(silent=True) or {}, d.child_id)
        warnings = _save(d, is_created=False)
        cert = start_certificate(d) if before != (d.domain, d.mode, d.fake_mode) and d.tls_status != "valid" else False
        return {"certificate_requested": cert, "warnings": warnings, "restart_mode": APPLY, **_list_out(d.child_id)}

    def delete(self, domain_id: int):
        """Remove a domain (at least one domain stays)"""
        d = _get_domain(domain_id)
        child_id = d.child_id
        if Domain.query.filter(Domain.child_id == child_id).count() <= 1:
            abort(400, _("at least one domain should exist"))
        try:
            warnings = domain_rules.before_delete(d)
        except domain_rules.DomainRuleError as e:
            abort(400, str(e))
        for other in Domain.query.filter(Domain.child_id == child_id).all():
            if other.server_domain_id == d.id:
                other.server_domain = None
        db.session.delete(d)
        db.session.commit()
        return {"warnings": warnings, "restart_mode": APPLY, **_list_out(child_id)}


class DomainsPageOrderApi(MethodView):
    decorators = [login_required(ROLES)]

    def put(self):
        """Save the order (the first domain is the panel's main one and comes first in configs)"""
        child_id = _child_id()
        ids = [int(i) for i in (request.get_json(silent=True) or {}).get("ids") or []]
        rows = {d.id: d for d in _domains(child_id)}
        if set(ids) != set(rows) or len(ids) != len(rows):
            abort(400, "The order must list every domain once")
        for pos, domain_id in enumerate(ids):
            rows[domain_id].sort_order = pos
        db.session.commit()
        return {"restart_mode": APPLY, **_list_out(child_id)}


class DomainsPageIpsApi(MethodView):
    decorators = [login_required(ROLES)]

    def get(self, domain_id: int):
        """Where the domain (or its server domain) points now, and whether that is this server"""
        d = _get_domain(domain_id)
        target = d.get_server() or d.domain
        if not target:
            return {"domain": d.domain, "target": "", "ips": []}
        mine = set(hutils.network.get_ips_lazy())
        ips = sorted(hutils.network.get_domain_ips(target), key=lambda ip: (ip.version, str(ip)))
        return {"domain": d.domain, "target": target, "ips": [{"ip": str(ip), "version": ip.version, "is_server_ip": ip in mine} for ip in ips]}


class DomainsPageDetectApi(MethodView):
    decorators = [login_required(ROLES)]

    def post(self):
        """Guess how a domain is set up (points here directly, behind which CDN, or another site for REALITY)"""
        from hiddifypanel.hutils.network.domain_detect import detect_domain

        name = normalize_domain_name(str((request.get_json(silent=True) or {}).get("domain") or ""))
        if not name or not DOMAIN_RE.match(name):
            abort(400, _("Should be a valid domain"))
        result = detect_domain(name.lstrip("*."))
        used = Domain.query.filter(Domain.domain == name, Domain.child_id == _child_id()).first()
        return {**result, "domain": name, "already_added": bool(used)}


class DomainsPageCertificateApi(MethodView):
    decorators = [login_required(ROLES)]

    def get(self, domain_id: int):
        """Certificate status (re-read from disk), and the state of a running request"""
        from hiddifypanel.proxy_v3.tls_store_sync import sync_tls_store_for_domain_id

        d = _get_domain(domain_id)
        try:
            sync_tls_store_for_domain_id(d.id)
        except Exception as e:
            logger.debug(f"TLS sync for {d.domain} failed: {e}")
        db.session.refresh(d)
        return _tls_out(d)

    def post(self, domain_id: int):
        """Ask for a real certificate now"""
        d = _get_domain(domain_id)
        if not d.need_valid_ssl:
            abort(400, "This domain uses a decoy certificate")
        if "*" in (d.domain or ""):
            abort(400, "Wildcard domains get their certificate from the CDN")
        start_certificate(d)
        return _tls_out(d)


class DomainsPagePortCheckApi(MethodView):
    decorators = [login_required(ROLES)]

    def get(self):
        """Can this port be a domain's TLS / HTTP gateway port? (free, or only used by haproxy / rpxy-l4)"""
        kind = request.args.get("kind", "tls")
        if kind not in ("tls", "http"):
            abort(400, "kind must be tls or http")
        try:
            port = int(request.args.get("port", ""))
        except ValueError:
            abort(400, "port must be a number")
        domain_id = request.args.get("domain_id", type=int)
        problem = port_problem(port, kind=kind, child_id=_child_id(), domain_id=domain_id)
        return {"port": port, "kind": kind, "ok": problem is None, **(problem or {})}
