from __future__ import annotations

from collections.abc import Iterator

from pydantic import BaseModel, ConfigDict, Field

from hiddifypanel.models import FakeMode
from hiddifypanel.models.custom_proxy import CustomProxyMode, CustomProxyTransport, L7Proto, ProxyProto, TlsLayer
from hiddifypanel.proxy_v3.context_vars.ip import IPVar

from .cert import CertVar
from .domain import DomainIPVar, _keeps_hostname, expand_sni_domain_servers
from .hconfig import HConfigVar
from .platform import PlatformVar
from .proxy import ClientBuilderProxyVar, ClientProxyDomainVar, is_download_upload_different
from .user import UserVar


class ClientContextVar(BaseModel):
    """Typed client-side template context."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    user: UserVar
    hconfig: HConfigVar
    platform: PlatformVar
    proxy: ClientBuilderProxyVar
    shared_cert: CertVar = Field(default_factory=CertVar.empty)
    client_proxy_tags: list[str] = Field(default_factory=list)
    # Client core being rendered (hiddify-core, singbox, xray, clash, sublink); set by the builders.
    render_core: str = ""
    # Rendering for a parent panel (child/client-configs): the parent adds its own groups and status.
    for_parent: bool = False
    # True → render only telegram proxies (mtproxies); False → all except telegram.
    include_telegram_links: bool = False

    def iter_ctx_domains(self) -> Iterator[ClientContextDomainVar]:
        domains = [domain for domain in self.proxy.domains if _client_domain_allowed(domain, self.proxy)]
        domains = expand_client_domains(self.proxy, domains)
        hidden = _hidden_config_names(self.platform)
        for domain in domains:
            if hidden and _config_name(self.proxy, domain) in hidden:
                continue  # failed the last config health check (setting config_health_hide_failed)
            yield ClientContextDomainVar(
                user=self.user,
                hconfig=self.hconfig,
                platform=self.platform,
                proxy=self.proxy.with_domain(domain),
                shared_cert=self.shared_cert,
                client_proxy_tags=list(self.client_proxy_tags),
                render_core=self.render_core,
                for_parent=self.for_parent,
                include_telegram_links=self.include_telegram_links,
            )


class ClientContextDomainVar(ClientContextVar):
    """Client context bound to one domain (``ctx.proxy.domain``)."""

    proxy: ClientProxyDomainVar


def _hidden_config_names(platform: PlatformVar) -> frozenset[str]:
    """Names of the configs to leave out for this client: the ones that failed the last config health check for its
    kind of app (empty unless the setting is on)."""
    from hiddifypanel.proxy_v3 import config_health

    hidden = config_health.hidden_configs()
    if not hidden or config_health.is_check_request():
        return frozenset()
    return hidden.get(config_health.health_app(getattr(platform.app_group, "name", platform.app_group)), frozenset())


def _config_name(proxy: ClientBuilderProxyVar, domain: DomainIPVar) -> str:
    """The config's name as the builtin client/tag template writes it (tag, domain alias or name, IP version, ALPN)."""
    from hiddifypanel.proxy_v3 import config_health

    parts = [proxy.tag, domain.alias or domain.name, domain.ip_version, getattr(proxy, "alpn", "") or ""]
    return config_health.config_name(" ".join(str(p) for p in parts if p))


def _client_domain_allowed(domain: DomainIPVar, proxy: ClientBuilderProxyVar) -> bool:
    if domain.is_sub_link_only():
        return False

    if domain.is_reality() and not is_reality_domain_valid(domain, proxy):
        return False
    # Download REALITY is a separate leg (xHTTP downloadSettings): validate the *download*
    # TLS layer, not the upload one. Using is_reality_domain_valid here dropped every config
    # whose upload was HTTP/H1/QUIC even when download was TLS H2 REALITY.
    # DomainIPVar.download is always a self-copy when no separate download domain is set —
    # only validate a REALITY download leg when upload/download actually differ.
    if (
        domain.download
        and domain.download.is_reality()
        and is_download_upload_different(domain, proxy)
        and not is_reality_download_leg_valid(proxy)
    ):
        return False

    return True


def expand_client_domains(proxy: ClientBuilderProxyVar, domains: list[DomainIPVar]) -> list[DomainIPVar]:
    domains = [domain for domain in domains if not domain.is_sub_link_only()]
    if proxy.mode == CustomProxyMode.no_inbound:
        return domains
    if proxy.mode == CustomProxyMode.ip:
        return _unique_ip_mode_domains(proxy, domains)
    expanded: list[DomainIPVar] = []
    for domain in domains:
        expanded.extend(expand_sni_domain_servers(domain))
    return expanded


def _ip_mode_domain_rank(domain: DomainIPVar) -> tuple[int, str]:
    if domain.fake_mode == FakeMode.reality:
        return (2, domain.name)
    if domain.fake_mode == FakeMode.fake:
        return (1, domain.name)
    return (0, domain.name)


def _unique_ip_mode_domains(proxy: ClientBuilderProxyVar, domains: list[DomainIPVar]) -> list[DomainIPVar]:
    """IP-mode clients connect by address:port; emit one entry per distinct IP.

    Domains with a bound ``server_domain`` or ``cdn_ip`` keep that address, and domains with ``resolve_ip`` off keep their
    hostname: neither is expanded.
    """
    # A better-ranked domain still claims a shared IP, but the entry stays where the
    # admin put that domain in the list (not alphabetical).
    unique: list[tuple[int, DomainIPVar, str]] = []
    seen: set[tuple[str, int]] = set()
    kept: list[tuple[int, DomainIPVar]] = []
    ranked = sorted(enumerate(domains), key=lambda item: (*_ip_mode_domain_rank(item[1]), item[0]))
    for index, domain in ranked:
        # A bound server domain / CDN IP, or "Resolve IP" off on a dialable hostname (the client resolves it, as for
        # the other proxies in expand_sni_domain_servers): kept as it is, not replaced by its IPs.
        if domain.keeps_dst_server or _keeps_hostname(domain):
            kept.append((index, domain))
            continue
        bound = proxy.with_domain(domain)
        port = int(bound.port or 0)
        candidates = [str(ip).strip() for ip in (domain.ips.ips if domain.ips else []) if str(ip).strip()]
        if not candidates:
            server = str(bound.server or "").strip()
            if server:
                candidates = [server]
        for ip in candidates:
            key = (ip, port)
            if key in seen:
                continue
            seen.add(key)
            unique.append((index, domain, ip))

    result: list[DomainIPVar] = [domain for _, domain in sorted(kept)]
    for _, domain, ip in sorted(unique):
        result.append(
            domain.model_copy(
                update={
                    "dst_server": ip,
                    "ips": IPVar.from_strings(ip),
                    "download": None,
                    "has_server_domain": False,
                }
            )
        )
    return result


# Xray REALITY works with VLESS / Trojan / VMess on tcp/raw, xhttp, and grpc
# (https://xtls.github.io/en/config/transport.html — security × protocol matrix).
_REALITY_PROTOS = frozenset({ProxyProto.vless, ProxyProto.trojan, ProxyProto.vmess})
_REALITY_TRANSPORTS = frozenset({CustomProxyTransport.xhttp, CustomProxyTransport.grpc, CustomProxyTransport.tcp, CustomProxyTransport.http})


def is_reality_domain_valid(domain: ClientProxyDomainVar | DomainIPVar, proxy: ClientBuilderProxyVar) -> bool:
    """Whether this proxy's *upload* leg can speak REALITY to ``domain``."""
    if domain.is_reality():
        if proxy.tls_layer in [TlsLayer.quic_tls, TlsLayer.http]:
            return False
        # http = raw TCP with an HTTP header ("rawhttp"); with TLS it can ride REALITY
        # (domain_mode_filter.transport_tls_supports_reality offers it the reality domain modes).
        if proxy.transport not in _REALITY_TRANSPORTS:
            return False
        if proxy.l7_reverse_proto not in [L7Proto.h2] and proxy.transport in [CustomProxyTransport.xhttp]:
            return False
        if proxy.mode != CustomProxyMode.domains_l7_gateway:
            return False
        if proxy.proto not in _REALITY_PROTOS:
            return False
    return True


def is_reality_download_valid(proxy: ClientBuilderProxyVar) -> bool:
    """xHTTP download REALITY only on TLS H2 (same rule as transport_tls_supports_reality)."""
    if proxy.transport != CustomProxyTransport.xhttp:
        return True
    layer = proxy.download_tls_layer if proxy.download_tls_layer is not None else proxy.tls_layer
    return layer == TlsLayer.tls_h2


def is_reality_download_leg_valid(proxy: ClientBuilderProxyVar) -> bool:
    """Whether this proxy can emit a REALITY downloadSettings leg (xHTTP download domain).

    Checks the download TLS layer; upload may be HTTP/H1/QUIC while download is TLS H2 REALITY.
    """
    if proxy.mode != CustomProxyMode.domains_l7_gateway:
        return False
    if proxy.transport != CustomProxyTransport.xhttp:
        # Download domain is only wired into xHTTP client templates.
        return False
    if proxy.proto not in _REALITY_PROTOS:
        return False
    return is_reality_download_valid(proxy)
