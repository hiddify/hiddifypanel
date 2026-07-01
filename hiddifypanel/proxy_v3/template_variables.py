from __future__ import annotations

import json
import time
from functools import lru_cache
from pathlib import Path
from typing import Any

from hiddifypanel import hutils
from hiddifypanel.models import Domain, User, get_hconfigs
from hiddifypanel.models.config_enum import config_enum_members

from .jinja_context import wrap_hconfigs
from hiddifypanel.proxy_v3.context_vars import DomainIPVar, ProxyVar

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
    ("include_path", 'Deployed sidecar path: include_path("haproxy/server/maps/path_v10")'),
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
    ("pinnedPeerCertSha256", "Pinned server cert public-key SHA-256 (base64)"),
    ("public_key_sha256", "Server cert public-key SHA-256 (base64)"),
    ("fingerprint", "Certificate public-key SHA-256 fingerprint (base64)"),
    ("valid_cert", "Whether stored certificate is valid and not expired"),
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


_STATIC_PROXY_SAMPLE: dict[str, Any] = ProxyVar(
    tag="tls_h2",
    path="test-path",
    domain=DomainIPVar(name="example.com", server="example.com", port=443),
).to_dict()


def _config_enum_members() -> list[Any]:
    return config_enum_members()


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


def _first_sample_user() -> User | None:
    return User.query.filter(User.enable.is_(True)).order_by(User.id).first()


def _first_sample_domain(child_id: int) -> Domain | None:
    return Domain.query.filter(Domain.child_id == child_id).order_by(Domain.id).first()


def build_domain_sample(child_id: int = 0) -> dict[str, Any]:
    domain_db = _first_sample_domain(child_id)
    if not domain_db:
        raise ValueError("No sample domain found")
    hconfigs = get_hconfigs(child_id)
    server_ipv4 = hutils.network.get_ip_str(4) or "203.0.113.1"
    server_ipv6 = hutils.network.get_ip_str(6) or "2001:db8::1"
    port = domain_db.internal_port_special or domain_db.internal_port_tuic or domain_db.internal_port_hysteria2 or 443
    return DomainIPVar.from_domain(
        domain_db,
        hconfigs,
        ipv4=server_ipv4,
        ipv6=server_ipv6,
        port=port,
    ).to_dict()


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
    if not domain_db:
        return {}

    hconfigs = get_hconfigs(child_id)
    if skip_network_lookup:
        server_ipv4 = server_ip or "203.0.113.1"
        server_ipv6 = "2001:db8::1"
    else:
        server_ipv4 = server_ip or hutils.network.get_ip_str(4) or "203.0.113.1"
        server_ipv6 = hutils.network.get_ip_str(6) or "2001:db8::1"
    port = domain_db.internal_port_special or domain_db.internal_port_tuic or domain_db.internal_port_hysteria2 or 443
    var = DomainIPVar.from_domain(
        domain_db,
        hconfigs,
        ipv4=server_ipv4,
        ipv6=server_ipv6,
        port=port,
    )
    if server_ip:
        var = var.model_copy(update={"server": server_ip})
        var.ipsv4 = [server_ip]
    return var.to_dict()


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
        user_dict["expire_days"] = user_db.remaining_days
        return user_dict, [user_dict]
    sample = {
        "uuid": "00000000-0000-0000-0000-000000000001",
        "id": 1,
        "name": "example-user",
        "ed25519_public_key": "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIHRlc3Q=",
        "wg_pk": "wg-private-key-sample",
        "wg_psk": "wg-psk-sample",
        "wg_ipv4": "10.90.0.2",
        "is_active": True,
        "usage_limit_GB": 1000,
        "current_usage_GB": 0,
        "expire_days": 90,
        "lang": "en",
    }
    return sample, [sample]


def _fetch_hconfigs_direct(child_id: int) -> dict:
    """Load hconfigs from DB without Redis cache (avoids slow/hung cache lookups)."""
    from hiddifypanel.models.config import BoolConfig, StrConfig

    out: dict = {}
    for row in BoolConfig.query.filter(BoolConfig.child_id == child_id).all():
        if row.key is not None:
            out[row.key] = row.value
    for row in StrConfig.query.filter(StrConfig.child_id == child_id).all():
        if row.key is None:
            continue
        val = row.value
        if row.key.type == int and val is not None:
            val = int(val)
        out[row.key] = val
    return out


def _sample_values(child_id: int) -> dict[str, Any]:
    """Lightweight live values — no Redis, no DNS, no template rendering."""
    raw_hconfigs = _fetch_hconfigs_direct(child_id)
    hconfigs = wrap_hconfigs(raw_hconfigs)

    sample_user = _first_sample_user()
    user_dict = sample_user.to_dict(dump_id=True) if sample_user else {}

    active_users = [u.to_dict(dump_id=True) for u in User.query.filter(User.enable.is_(True)).order_by(User.id).limit(5).all()]
    users_serialized = _serialize(active_users)

    values: dict[str, Any] = {}

    for cfg_enum in _config_enum_members():
        key = getattr(cfg_enum, "name", None) or str(cfg_enum)
        current = raw_hconfigs.get(cfg_enum)
        if current is None:
            current = raw_hconfigs.get(key)
        if current is None:
            current = hconfigs.get(key)
        values[f"hconfigs.{key}"] = _mask_value(key, _serialize(current))

    for field, _ in USER_DICT_KEYS:
        val = user_dict.get(field)
        if field == "uuid_hex" and not val:
            val = str(user_dict.get("uuid") or "").replace("-", "")
        values[f"user.{field}"] = _mask_value(field, _serialize(val))

    values["users"] = users_serialized
    values["users"] = users_serialized

    for name, _ in CUSTOM_PROXY_VARS:
        values[f"{{{{ {name} }}}}"] = "…"
    values["custom_path"] = "test-path"

    for field, _ in PROXY_VAR_KEYS:
        values[f"proxy.{field}"] = _serialize(_STATIC_PROXY_SAMPLE.get(field))
    for field, _ in PROXY_INFO_KEYS:
        values[f"proxy.{field}"] = "—"

    context_values: dict[str, Any] = {
        "users": users_serialized,
        "domains": "…",
        "hconfigs": f"({len(raw_hconfigs)} settings)",
        "chconfigs": "…",
        "ConfigEnum": "ConfigEnum",
        "remarks": "…",
        "exec": "shell helper",
        "enumerate": "enumerate()",
        "skip": "skip()",
    }
    for name, _ in CONTEXT_ROOT_VARS:
        values[name] = context_values.get(name, "…")

    for name, _ in LOOP_VARS:
        values[name] = "—"

    return values


def _attach_values(groups: list[dict[str, Any]], values: dict[str, Any]) -> None:
    for group in groups:
        for var in group.get("variables") or []:
            var["value"] = values.get(var["access"])


def _enrich_catalog_with_values(child_id: int, lang: str) -> list[dict[str, Any]]:
    cache_key = (child_id, lang)
    now = time.monotonic()
    cached = _values_cache.get(cache_key)
    if cached and (now - cached[0]) < _VALUES_CACHE_TTL:
        return cached[1]

    groups = _clone_catalog(lang)
    _attach_values(groups, _sample_values(child_id))
    sample_user = _first_sample_user()
    if sample_user:
        display = (sample_user.name or sample_user.username or "").strip()
        if display:
            for group in groups:
                if group.get("id") == "user":
                    group["label"] = f"User (sample: {display})"
                    break
    _values_cache[cache_key] = (now, groups)
    return groups


def build_template_variables(
    child_id: int = 0,
    lang: str = "en",
    *,
    include_values: bool = False,
) -> list[dict[str, Any]]:
    if include_values:
        return _enrich_catalog_with_values(child_id, lang)
    return _clone_catalog(lang)


def flatten_template_variables(groups: list[dict[str, Any]]) -> list[dict[str, Any]]:
    flat: list[dict[str, Any]] = []
    for group in groups:
        for var in group.get("variables") or []:
            flat.append({**var, "category_label": group.get("label"), "category": var.get("category") or group.get("id")})
    return flat
