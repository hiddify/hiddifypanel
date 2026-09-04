from __future__ import annotations

import json
import time
from functools import lru_cache
from pathlib import Path
from typing import Any

from hiddifypanel import hutils
from hiddifypanel.models import Domain, User, get_hconfigs
from hiddifypanel.models.config_enum import config_enum_members

from hiddifypanel.proxy_v3.context_vars.domain import DomainIPVar
from hiddifypanel.proxy_v3.context_vars.proxy import ProxyVar

_TRANSLATIONS_ROOT = Path(__file__).resolve().parents[2] / "translations.i18n"

_VALUES_CACHE_TTL = 90
_values_cache: dict[tuple[int, str], tuple[float, list[dict[str, Any]]]] = {}

CUSTOM_PROXY_VARS: list[tuple[str, str]] = [
    ("IP", "Server IP (ip-based proxies; also domain.ip)"),
    ("DOMAIN", "Deprecated — use domain.name"),
    ("USER", "Current user object (dict)"),
    ("USER.uuid", "Current user UUID"),
    ("USERS", "Alias for users"),
    ("users", "List of active users in server templates"),
]

CONTEXT_ROOT_VARS: list[tuple[str, str]] = [
    ("user", "Current user (UserVar)"),
    ("domain", "Connection domain (DomainVar)"),
    ("hconfig", "Filtered panel settings (HConfigVar)"),
    ("platform", "Client platform from User-Agent (PlatformVar)"),
    ("proxy", "Current proxy link (ProxyVar: tag, port, path, server, …)"),
    ("users", "Active users (server inbound templates)"),
    ("users", "Active users for custom proxy server inbound templates"),
    ("domains", "Panel domains with ports and SSL flags"),
    ("hconfigs", "Legacy panel settings dict"),
    ("chconfigs", "Per-child settings dict (server config render)"),
    ("ConfigEnum", "Config key enum for hconfig()"),
    ("remarks", "Client config profile title"),
    ("exec", "Shell command helper (server templates only)"),
    ("enumerate", "Python enumerate in templates"),
    ("include_path", 'Deployed sidecar path: include_path(ctx, "haproxy/server/maps/path_v10")'),
    ("skip", "Callable — {{ skip() }} skips rendering this proxy"),
    ("SKIP", "Literal marker — output SKIP to skip this proxy"),
]

DOMAIN_DICT_KEYS: list[tuple[str, str]] = [
    ("name", "Domain hostname"),
    ("mode", "Domain mode (direct, cdn, special, …)"),
    ("alias", "Display alias"),
    ("cdn_ip", "CDN IP if set"),
    ("servernames", "SNI server names list"),
    ("internal_port_special", "REALITY / special inbound port"),
    ("internal_port_tuic", "TUIC inbound port"),
    ("internal_port_hysteria2", "Hysteria2 inbound port"),
    ("internal_port_naive", "Naive inbound port"),
    ("need_valid_ssl", "Whether valid SSL cert is required"),
    ("child_id", "Child panel id"),
]

DOMAIN_DERIVED_KEYS: list[tuple[str, str]] = [
    ("sni", "TLS SNI hostname"),
    ("host", "Host header / domain host"),
    ("server", "Connection server address"),
    ("port", "Proxy port"),
    ("ip", "Resolved connection IP (alias of server)"),
    ("ipv4", "Primary IPv4 (resolved or server)"),
    ("ipv6", "Primary IPv6 (resolved or server)"),
    ("ips", "All resolved domain IPs"),
    ("ipsv4", "Resolved IPv4 addresses"),
    ("ipsv6", "Resolved IPv6 addresses"),
]

DOMAIN_CERT_KEYS: list[tuple[str, str]] = [
    ("certificate", "TLS certificate PEM"),
    ("private_key", "TLS private key PEM"),
    ("cert_lines", "TLS certificate PEM lines (JSON array)"),
    ("key_lines", "TLS private key PEM lines (JSON array)"),
    ("cert_path", "TLS certificate file path"),
    ("key_path", "TLS private key file path"),
    ("verifyPeerCertByName", "Verify server certificate hostname"),
    ("pinnedPeerCertSha256", "Xray pinnedPeerCertSha256: SHA-256 of the leaf cert (lowercase hex)"),
    ("public_key_sha256", "sing-box certificate_public_key_sha256: SPKI SHA-256 (base64)"),
    ("fingerprint", "Xray certificate SHA-256 fingerprint (lowercase hex)"),
    ("valid_cert", "Whether stored certificate is valid and not expired"),
    ("self_signed", "Whether the certificate is self-signed"),
    ("expires_at", "Certificate expiry (ISO datetime)"),
    ("issuer", "Certificate issuer / CA name"),
    ("auto_renew", "Whether certificate is eligible for automatic renewal"),
    ("last_renewal_error", "Last certificate sync/renewal error message"),
]

PLATFORM_VAR_KEYS: list[tuple[str, str]] = [
    ("os", "OS facet (platform.os.name, platform.os.version)"),
    ("os_version", "OS version string (legacy flat field)"),
    ("root_access", "Whether client has root access"),
    ("app", "Client app facet (platform.app.name, platform.app.version)"),
    ("app_version", "Client app version string (legacy flat field)"),
    ("app_group", "App family facet (platform.app_group.name / .version)"),
    ("app_group_version", "Core version for app group"),
    ("singbox", "sing-box version facet (platform.singbox.version)"),
    ("hiddify", "Hiddify app version facet (platform.hiddify.version)"),
    ("useragent", "Raw User-Agent string"),
    ("tls_engine", "TLS engine: go, apple, windows"),
    ("compare_version", "platform.compare_version(a, b) → -1, 0, or 1"),
]

USER_DICT_KEYS: list[tuple[str, str]] = [
    ("uuid", "User UUID (vless/vmess id)"),
    ("uuid_hex", "User UUID without dashes"),
    ("name", "Display name"),
    ("username", "Login username"),
    ("id", "Numeric user id"),
    ("lang", "User language"),
    ("usage_limit_GB", "Traffic limit in GB"),
    ("current_usage_GB", "Current usage in GB"),
    ("expire_days", "Days remaining until expiry"),
    ("package_days", "Package duration days"),
    ("mode", "Reset mode (daily, weekly, …)"),
    ("is_active", "Whether user can connect"),
    ("enable", "Account enabled flag"),
    ("ed25519_public_key", "SSH public key"),
    ("ed25519_private_key", "SSH private key (server only)"),
    ("wg_pk", "WireGuard private key"),
    ("wg_pub", "WireGuard public key"),
    ("wg_psk", "WireGuard pre-shared key"),
    ("added_by_uuid", "Admin who created the user"),
]

PROXY_VAR_KEYS: list[tuple[str, str]] = [
    ("tag", "Proxy tag / ALPN / inbound tag"),
    ("port", "Proxy connection port"),
    ("path", "Proxy HTTP path (no leading /)"),
    ("server", "Connection host (domain.server or panel IP when ip-based)"),
    ("public_access", "Direct public port access enabled"),
    ("domain_binding", "domain or ip — whether templates use domain or server IP"),
    ("alpn", "ALPN tag string (defaults to tag)"),
]

PROXY_INFO_KEYS: list[tuple[str, str]] = [
    ("name", "Proxy display name"),
    ("proto", "Protocol (vless, vmess, trojan, …)"),
    ("transport", "Transport (ws, tcp, grpc, …)"),
    ("l3", "Layer 3 security (tls, reality, …)"),
    ("uuid", "User UUID for this link"),
    ("alpn", "ALPN string"),
    ("proxy_path", "Secret proxy path"),
    ("extra_info", "Domain alias in link name"),
    ("fingerprint", "uTLS fingerprint"),
    ("path", "URL path segment"),
    ("password", "Protocol password"),
    ("allow_insecure", "Allow insecure TLS"),
    ("cdn", "CDN mode flag"),
    ("reality_pbk", "REALITY public key"),
    ("reality_short_id", "REALITY short id"),
    ("flow", "VLESS flow (e.g. xtls-rprx-vision)"),
    ("fakedomain", "Fake TLS domain"),
    ("shared_secret", "ShadowTLS / SS shared secret"),
]

LOOP_VARS: list[tuple[str, str]] = [
    ("u", "Single user in {% for u in users %}"),
    ("d", "Single domain in {% for d in domains %}"),
    ("domain", "Domain hostname string in inbound loops"),
    ("port", "Inbound port in domain loops"),
    ("protocol", "Protocol name in generator loops"),
    ("stream", "Transport stream name"),
    ("path", "Combined path from hconfigs"),
    ("flow", "VLESS flow setting"),
    ("sid", "REALITY short id"),
    ("cert", "SSL certificate path (set in template)"),
    ("region", "Geo routing region"),
    ("site", "Geo site rule tag"),
]


@lru_cache(maxsize=8)
def _load_config_i18n(lang: str) -> dict[str, Any]:
    path = _TRANSLATIONS_ROOT / f"{lang}.json"
    if not path.is_file():
        path = _TRANSLATIONS_ROOT / "en.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except OSError:
        return {}
    return data.get("config") or {}


def _mask_value(name: str, value: Any) -> Any:
    lowered = name.lower()
    if any(token in lowered for token in ("secret", "private_key", "_pk", "password", "admin_secret")):
        text = str(value or "")
        if len(text) > 12:
            return f"{text[:6]}…{text[-4:]}"
    return value


def _serialize(value: Any, *, max_str: int = 200) -> Any:
    if value is None or isinstance(value, (bool, int, float)):
        return value
    if isinstance(value, str):
        return value if len(value) <= max_str else f"{value[:max_str]}…"
    if isinstance(value, (list, tuple)):
        if len(value) > 5:
            return [_serialize(v, max_str=max_str) for v in value[:5]] + ["…"]
        return [_serialize(v, max_str=max_str) for v in value]
    if isinstance(value, dict):
        if len(value) > 12:
            preview = {k: _serialize(v, max_str=max_str) for k, v in list(value.items())[:8]}
            preview["…"] = f"({len(value)} keys)"
            return preview
        return {k: _serialize(v, max_str=max_str) for k, v in value.items()}
    if hasattr(value, "value"):
        return value.value
    text = str(value)
    return text if len(text) <= max_str else f"{text[:max_str]}…"


def _entry(
    category: str,
    access: str,
    label: str,
    description: str,
    *,
    name: str | None = None,
    access_bracket: str | None = None,
) -> dict[str, Any]:
    return {
        "category": category,
        "name": name if name is not None else label,
        "access": access,
        "access_bracket": access_bracket if access_bracket is not None else access,
        "label": label,
        "description": description,
    }


@lru_cache(maxsize=8)
def _build_static_catalog(lang: str) -> tuple[dict[str, Any], ...]:
    config_i18n = _load_config_i18n(lang)
    groups: list[dict[str, Any]] = []

    hconfig_vars = []
    for cfg_enum in sorted(_config_enum_members(), key=lambda c: getattr(c, "name", "")):
        key = cfg_enum.name
        cfg = config_i18n.get(key) or {}
        label = cfg.get("label") or key.replace("_", " ").title()
        description = cfg.get("description") or ""
        hconfig_vars.append(
            _entry(
                "hconfig",
                f"hconfig.{key}",
                label,
                description,
                name=key,
                access_bracket=f"hconfig['{key}']",
            )
        )
    groups.append({"id": "hconfig", "label": "Panel settings (hconfig)", "variables": hconfig_vars})

    user_vars = [_entry("user", f"user.{field}", field.replace("_", " ").title(), desc, name=field, access_bracket=f"user['{field}']") for field, desc in USER_DICT_KEYS]
    groups.append({"id": "user", "label": "User (sample: first active user)", "variables": user_vars})

    groups.append(
        {
            "id": "users",
            "label": "Users list",
            "variables": [
                _entry("users", "users", "Active users", "List of active users in {% for u in users %} loops (server configs)"),
                _entry("users", "users", "Available users", "Active users for custom proxy server inbound templates"),
            ],
        }
    )

    domain_vars = []
    for field, desc in DOMAIN_DICT_KEYS:
        access = f"domain.{field}"
        bracket = "domain" if field == "name" else f"d['{field}']"
        domain_vars.append(_entry("domain", access, field, desc, access_bracket=bracket))
    for field, desc in DOMAIN_DERIVED_KEYS:
        domain_vars.append(_entry("domain", f"domain.{field}", field, desc))
    for field, desc in DOMAIN_CERT_KEYS:
        domain_vars.append(_entry("domain", f"domain.cert.{field}", field, desc))
    groups.append({"id": "domain", "label": "Domain (sample: first domain)", "variables": domain_vars})

    platform_vars = [_entry("platform", f"platform.{field}", field, desc, name=field) for field, desc in PLATFORM_VAR_KEYS]
    groups.append({"id": "platform", "label": "Client platform (User-Agent)", "variables": platform_vars})

    proxy_vars = [_entry("proxy", f"proxy.{field}", field, desc, name=field) for field, desc in PROXY_VAR_KEYS]
    proxy_vars.extend(_entry("proxy", field, field, desc, name=field) for field, desc in PROXY_INFO_KEYS)
    groups.append({"id": "proxy", "label": "Proxy (current link)", "variables": proxy_vars})

    cp_vars = [_entry("custom_proxy", f"{{{{ {name} }}}}", name, desc, name=name) for name, desc in CUSTOM_PROXY_VARS]
    groups.append({"id": "custom_proxy", "label": "Custom proxy placeholders", "variables": cp_vars})

    root_vars = [_entry("context", name, name, desc) for name, desc in CONTEXT_ROOT_VARS]
    groups.append({"id": "context", "label": "Template context roots", "variables": root_vars})

    loop_var_entries = [_entry("loop", name, name, desc) for name, desc in LOOP_VARS]
    groups.append({"id": "loop", "label": "Loop / inbound variables", "variables": loop_var_entries})

    return tuple(groups)


def _clone_catalog(lang: str) -> list[dict[str, Any]]:
    return [dict(g, variables=[dict(v) for v in g["variables"]]) for g in _build_static_catalog(lang)]


_STATIC_DOMAIN_SAMPLE: dict[str, Any] = {
    "name": "example.com",
    "sni": "example.com",
    "host": "example.com",
    "server": "203.0.113.1",
    "port": 443,
    "ip": "203.0.113.1",
    "ipv4": "203.0.113.1",
    "ipv6": "2001:db8::1",
    "mode": "direct",
    "alias": "example",
}


def _first_sample_user() -> User | None:
    return User.query.filter(User.enable.is_(True)).order_by(User.id).first()


def _first_sample_domain(child_id: int) -> Domain | None:
    return Domain.query.filter(Domain.child_id == child_id).order_by(Domain.id).first()


def _domain_dict_from_db(
    domain_db: Domain,
    *,
    child_id: int,
    server_ip: str | None = None,
    skip_network_lookup: bool = False,
) -> dict[str, Any]:
    hconfigs = get_hconfigs(child_id)
    extracted = hutils.proxy.sni_host_server_extractor(domain_db, hconfigs)
    if skip_network_lookup:
        server_ipv4 = server_ip or "203.0.113.1"
        server_ipv6 = "2001:db8::1"
    else:
        server_ipv4 = server_ip or hutils.network.get_ip_str(4) or "203.0.113.1"
        server_ipv6 = hutils.network.get_ip_str(6) or "2001:db8::1"
    port = domain_db.internal_port_special or domain_db.internal_port_tuic or domain_db.internal_port_hysteria2 or 443
    server = server_ip or extracted.get("server") or domain_db.domain
    base = domain_db.to_dict(dump_ports=True, dump_child_id=True)
    base.update(
        {
            "name": str(domain_db.domain or "").lower(),
            "id": domain_db.id,
            "domain_id": domain_db.id,
            "sni": extracted.get("sni"),
            "host": extracted.get("host"),
            "server": server,
            "port": port,
            "ip": server,
            "ipv4": server_ipv4,
            "ipv6": server_ipv6,
            "ips": [server],
            "ipsv4": [server_ipv4] if server_ipv4 else [],
            "ipsv6": [server_ipv6] if server_ipv6 else [],
            "allow_insecure": extracted.get("allow_insecure"),
            "cdn": extracted.get("cdn"),
        }
    )
    if "reality_pbk" in extracted:
        base["reality_pbk"] = extracted["reality_pbk"]
    if "reality_short_id" in extracted:
        base["reality_short_id"] = extracted["reality_short_id"]
    return base


def build_domain_sample(child_id: int = 0) -> dict[str, Any]:
    domain_db = _first_sample_domain(child_id)
    if not domain_db:
        return dict(_STATIC_DOMAIN_SAMPLE)
    return _domain_dict_from_db(domain_db, child_id=child_id)


def build_domain_context(
    child_id: int = 0,
    *,
    domain_id: int | None = None,
    domain_host: str | None = None,
    server_ip: str | None = None,
    skip_network_lookup: bool = False,
) -> dict[str, Any]:
    domain_db = None
    if domain_id is not None:
        domain_db = Domain.query.filter(Domain.id == domain_id, Domain.child_id == child_id).first()
    elif domain_host:
        domain_db = Domain.query.filter(
            Domain.child_id == child_id,
            Domain.domain == domain_host.strip(),
        ).first()

    if domain_db:
        return _domain_dict_from_db(
            domain_db,
            child_id=child_id,
            server_ip=server_ip,
            skip_network_lookup=skip_network_lookup,
        )

    host = (domain_host or "").strip() or str(_STATIC_DOMAIN_SAMPLE.get("name") or "example.com")
    server = server_ip or host
    return {
        "name": host,
        "sni": host,
        "host": host,
        "server": server,
        "port": 443,
        "ip": server,
        "ipv4": server_ip or server,
        "ipv6": "2001:db8::1",
        "ips": [server],
        "ipsv4": [server_ip or server],
        "ipsv6": [],
        "mode": "direct",
        "alias": host,
    }


def build_user_context(
    *,
    user_id: int | None = None,
    user_uuid: str | None = None,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    user_db = None
    if user_id is not None:
        user_db = User.query.filter(User.id == user_id).first()
    elif user_uuid:
        user_db = User.by_uuid(user_uuid)
    if not user_db:
        user_db = _first_sample_user()
    if user_db:
        user_dict = user_db.to_dict(dump_id=True)
        return user_dict, [user_dict]
    sample = {
        "uuid": "00000000-0000-0000-0000-000000000001",
        "id": 1,
        "name": "example-user",
        "ed25519_public_key": "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIHRlc3Q=",
        "wg_pk": "wg-private-key-sample",
        "wg_psk": "wg-psk-sample",
        "wg_ipv4": "10.90.0.2",
    }
    return sample, [sample]


def _config_enum_members() -> list[Any]:
    return [c for c in config_enum_members() if getattr(c, "name", "") != "dbvalues"]


def build_template_variables(
    child_id: int = 0,
    lang: str = "en",
    *,
    include_values: bool = False,
) -> list[dict[str, Any]]:
    groups = _clone_catalog(lang)
    if not include_values:
        return groups

    sample_domain = build_domain_sample(child_id)
    user_dict, users = build_user_context()
    for group in groups:
        for var in group.get("variables") or []:
            access = str(var.get("access") or "")
            if access.startswith("domain."):
                var["value"] = sample_domain.get(access.split(".", 1)[1])
            elif access == "users":
                var["value"] = users
            elif access.startswith("user."):
                var["value"] = user_dict.get(access.split(".", 1)[1])
    return groups
