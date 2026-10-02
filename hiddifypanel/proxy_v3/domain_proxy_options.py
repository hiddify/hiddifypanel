from __future__ import annotations

from hiddifypanel.models import CustomProxy, CustomProxyMode, DomainType, FakeMode

from .domain_mode_filter import domain_modes_use_reality, expand_domain_mode_tokens, proxy_buckets_for_domain

REALITY_TERMINATION_SLUG = "xray-reality-termination"

_PROXY_GROUP_ORDER = (
    ("sni_gateway", 0),
    ("dns_gateway", 1),
    ("ip_based", 2),
    ("l7_gateway", 3),
    ("other", 4),
)


def proxy_mode_group(mode: CustomProxyMode | None) -> str:
    if mode == CustomProxyMode.domains_sni_gateway:
        return "sni_gateway"
    if mode == CustomProxyMode.domains_l7_gateway:
        return "l7_gateway"
    if mode == CustomProxyMode.domains_dns_gateway:
        return "dns_gateway"
    if mode in (
        CustomProxyMode.ip,
        CustomProxyMode.domains_auto_public_ports,
        CustomProxyMode.domains_single_public_port,
    ):
        return "ip_based"
    return "other"


def _proxy_sort_key(proxy: CustomProxy) -> tuple:
    group = proxy_mode_group(proxy.mode)
    group_rank = next(rank for key, rank in _PROXY_GROUP_ORDER if key == group)
    return (group_rank, int(proxy.sort_order or 0), str(proxy.name or ""), int(proxy.id or 0))


def _proxy_payload(proxy: CustomProxy) -> dict:
    return {
        "id": proxy.id,
        "name": proxy.name,
        "slug": proxy.slug,
        "mode": proxy.mode.value if proxy.mode else None,
        "group": proxy_mode_group(proxy.mode),
        "domain_modes": list(proxy.domain_modes or []),
    }


def list_domain_proxy_options(
    *,
    child_id: int,
    mode: DomainType,
    fake_mode: FakeMode,
) -> list[dict]:
    buckets = set(proxy_buckets_for_domain(mode, fake_mode))
    rows: list[CustomProxy] = []
    for proxy in CustomProxy.query.filter(
        CustomProxy.enable == True,
        CustomProxy.child_id == child_id,
    ).all():
        if not proxy.enable or proxy.slug == REALITY_TERMINATION_SLUG:
            continue
        if fake_mode == FakeMode.reality:
            if proxy.mode != CustomProxyMode.domains_l7_gateway or not domain_modes_use_reality(proxy.domain_modes):
                continue
        proxy_buckets = expand_domain_mode_tokens(proxy.domain_modes)
        if buckets & proxy_buckets:
            rows.append(proxy)

    rows.sort(key=_proxy_sort_key)
    return [_proxy_payload(proxy) for proxy in rows]
