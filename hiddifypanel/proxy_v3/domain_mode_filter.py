from __future__ import annotations

from typing import Any, Iterable, Protocol

DOMAIN_MODE_DIRECT_VALID = "direct-valid"
DOMAIN_MODE_DIRECT_FAKE = "direct-fake"
DOMAIN_MODE_DIRECT_REALITY = "direct-reality"
DOMAIN_MODE_DIRECT_DNS = "direct-dns"
DOMAIN_MODE_RELAY_VALID = "relay-valid"
DOMAIN_MODE_RELAY_FAKE = "relay-fake"
DOMAIN_MODE_RELAY_REALITY = "relay-reality"
DOMAIN_MODE_CDN = "cdn"

DOMAIN_MODE_VALUES: tuple[str, ...] = (
    DOMAIN_MODE_DIRECT_VALID,
    DOMAIN_MODE_DIRECT_FAKE,
    DOMAIN_MODE_DIRECT_REALITY,
    DOMAIN_MODE_DIRECT_DNS,
    DOMAIN_MODE_RELAY_VALID,
    DOMAIN_MODE_RELAY_FAKE,
    DOMAIN_MODE_RELAY_REALITY,
)
ALLOWED_DOMAIN_MODES: tuple[str, ...] = DOMAIN_MODE_VALUES + (DOMAIN_MODE_CDN,)
CDN_CAPABLE_TRANSPORTS = frozenset({"xhttp", "grpc", "ws", "httpupgrade"})
_REALITY_TLS_LAYERS = frozenset({"tls", "tls_h2"})
_NO_REALITY_TLS_LAYERS = frozenset({"http", "tls_h1", "quic_tls", "quic_tcp_tls"})

V2RAY_ALL_DOMAIN_MODES = DOMAIN_MODE_VALUES
VALID_DIRECT_RELAY_DOMAIN_MODES = (DOMAIN_MODE_DIRECT_VALID, DOMAIN_MODE_RELAY_VALID)
FAKE_DIRECT_RELAY_DOMAIN_MODES = (DOMAIN_MODE_DIRECT_FAKE, DOMAIN_MODE_RELAY_FAKE)
VALID_FAKE_DIRECT_RELAY_DOMAIN_MODES = (
    DOMAIN_MODE_DIRECT_VALID,
    DOMAIN_MODE_DIRECT_FAKE,
    DOMAIN_MODE_RELAY_VALID,
    DOMAIN_MODE_RELAY_FAKE,
)
REALITY_DIRECT_RELAY_DOMAIN_MODES = (DOMAIN_MODE_DIRECT_REALITY, DOMAIN_MODE_RELAY_REALITY)
DNS_DIRECT_DOMAIN_MODES = (DOMAIN_MODE_DIRECT_DNS,)

_CDN_TYPES = frozenset({"cdn", "auto_cdn_ip", "worker"})
_DIRECT_TYPES = frozenset({"direct", "old_xtls_direct", "dnstt", "sub_link_only"})

_LEGACY_EXPAND: dict[str, tuple[str, ...]] = {
    "direct": (DOMAIN_MODE_DIRECT_VALID,),
    "relay": (DOMAIN_MODE_RELAY_VALID,),
    "fake": FAKE_DIRECT_RELAY_DOMAIN_MODES,
    "reality": REALITY_DIRECT_RELAY_DOMAIN_MODES,
    "special": REALITY_DIRECT_RELAY_DOMAIN_MODES,
    "dns": DNS_DIRECT_DOMAIN_MODES,
}


class _DomainLike(Protocol):
    mode: Any
    fake_mode: Any


def _enum_value(value: Any) -> str:
    raw = getattr(value, "value", value)
    return str(raw or "").strip().lower()


def _access_for_domain_type(mode: Any) -> str | None:
    value = _enum_value(mode)
    if value in _DIRECT_TYPES:
        return "direct"
    if value == "relay":
        return "relay"
    return None


def domain_compound_mode(mode: Any, fake_mode: Any) -> str | None:
    access = _access_for_domain_type(mode)
    cert = _enum_value(fake_mode) or "valid"
    if access:
        return f"{access}-{cert}"
    if _enum_value(mode) in _CDN_TYPES and cert == "valid":
        return "cdn"
    return None


def expand_domain_mode_tokens(modes: Iterable[str] | None) -> set[str]:
    out: set[str] = set()
    for raw in modes or []:
        token = str(raw).strip().lower()
        if not token:
            continue
        if token in ALLOWED_DOMAIN_MODES:
            out.add(token)
            continue
        out.update(_LEGACY_EXPAND.get(token, ()))
    return out


def normalize_domain_modes(modes: Iterable[str] | None, *, default: Iterable[str] | None = None) -> list[str]:
    expanded = expand_domain_mode_tokens(modes)
    out = [token for token in ALLOWED_DOMAIN_MODES if token in expanded]
    if out:
        return out
    seen: set[str] = set()
    for token in default or ():
        key = str(token).strip().lower()
        if key in ALLOWED_DOMAIN_MODES and key not in seen:
            seen.add(key)
            out.append(key)
    return out


def transport_tls_supports_reality(transport: str | None, tls_layer: str | None) -> bool:
    """REALITY is only supported on gRPC, xHTTP H2, and raw HTTP with TLS."""
    transport_key = str(transport or "").strip().lower()
    layer = str(tls_layer or "").strip().lower()
    if not transport_key or layer in _NO_REALITY_TLS_LAYERS:
        return False
    if transport_key == "grpc":
        return layer in _REALITY_TLS_LAYERS
    if transport_key == "xhttp":
        return layer == "tls_h2"
    if transport_key == "http":
        return layer in _REALITY_TLS_LAYERS
    return False


def domain_mode_is_reality(token: str) -> bool:
    key = str(token).strip().lower()
    return key in {"reality", "special"} or key.endswith("-reality")


def domain_modes_use_reality(domain_modes: list[str] | None) -> bool:
    return any(domain_mode_is_reality(token) for token in (domain_modes or []))


def filter_domain_modes_without_reality(domain_modes: list[str] | tuple[str, ...]) -> list[str]:
    return [mode for mode in domain_modes if not domain_mode_is_reality(mode)]


def _domain_matches_bucket(domain: _DomainLike, bucket: str) -> bool:
    compound = domain_compound_mode(domain.mode, domain.fake_mode)
    if not compound:
        return False
    return compound in expand_domain_mode_tokens([bucket])


def proxy_buckets_for_domain(mode: Any, fake_mode: Any) -> list[str]:
    compound = domain_compound_mode(mode, fake_mode)
    return [compound] if compound else []


def domain_matches_modes(domain: _DomainLike, modes: list[str]) -> bool:
    if not modes:
        return True
    return any(_domain_matches_bucket(domain, bucket) for bucket in modes)


def domain_ip_matches_modes(domain: _DomainLike, modes: list[str]) -> bool:
    if not modes:
        return True
    return any(_domain_matches_bucket(domain, bucket) for bucket in modes)
